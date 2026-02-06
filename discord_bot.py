import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

# Global command queue for communication with FF bot
command_queue = asyncio.Queue()
status_data = {
    "bot_online": False,
    "active_teams": [],
    "last_command": None
}

class DiscordFFBot(commands.Bot):
    def __init__(self, config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        
        super().__init__(command_prefix=config['discord']['prefix'], intents=intents)
        
        self.config = config
        try:
            self.command_channel_id = int(config['discord']['command_channel_id'])
        except (ValueError, TypeError, KeyError):
            print("❌ Error: Invalid or missing Discord Channel ID!")
            self.command_channel_id = 0
        
    async def setup_hook(self):
        """Called when bot is starting up"""
        print("🤖 Discord Bot is starting up...")
        
    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        print(f'✅ DISCORD SUCCESS: Logged in as {self.user.name} (ID: {self.user.id})')
        print(f'📢 Channel: {self.command_channel_id} | Prefix: {self.command_prefix}')
        print('━' * 50)
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Free Fire Commands | /help"
            )
        )
    
    async def on_message(self, message):
        """Process messages from the designated channel"""
        # Ignore bot's own messages
        if message.author == self.user:
            return
        
        # Only process messages from the designated channel
        if message.channel.id != self.command_channel_id:
            return
        
        # Process commands
        await self.process_commands(message)

# Create bot instance (will be initialized in main)
bot = None

def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if not os.path.exists(config_path):
        print("❌ Error: config.json not found!")
        print("Please create config.json with your Discord bot token and channel ID")
        return None
    
    with open(config_path, 'r') as f:
        return json.load(f)

@commands.command(name='lw')
async def start_levelup(ctx, teamcode: str = None):
    """Start level-up bot for a team code
    
    Usage: /lw [teamcode]
    Example: /lw 444854
    """
    if not teamcode:
        await ctx.send("❌ **Error**: Please provide a team code!\n**Usage**: `!lw [teamcode]`\n**Example**: `!lw 444854`")
        return
    
    # Validate teamcode (should be numeric)
    if not teamcode.isdigit():
        await ctx.send(f"❌ **Error**: Team code must be numeric!\n**Received**: `{teamcode}`")
        return
    
    # Add command to queue
    await command_queue.put({
        'type': 'start',
        'teamcode': teamcode,
        'timestamp': datetime.now().isoformat(),
        'user': str(ctx.author)
    })
    
    status_data['last_command'] = f"!lw {teamcode}"
    if teamcode not in status_data['active_teams']:
        status_data['active_teams'].append(teamcode)
    
    embed = discord.Embed(
        title="🎮 Free Fire Bot Activated!",
        description=f"Starting level-up loop for team **{teamcode}**",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Team Code", value=f"`{teamcode}`", inline=True)
    embed.add_field(name="Requested By", value=ctx.author.mention, inline=True)
    embed.set_footer(text="DHASU-RUSHER Bot")
    
    await ctx.send(embed=embed)
    
    if bot.config['settings']['log_discord_commands']:
        print(f"📨 Discord Command: !lw {teamcode} by {ctx.author}")

@commands.command(name='stop')
async def stop_levelup(ctx, teamcode: str = None):
    """Stop level-up bot for a team code
    
    Usage: /stop [teamcode]
    Example: /stop 444854
    """
    if not teamcode:
        await ctx.send("❌ **Error**: Please provide a team code!\n**Usage**: `!stop [teamcode]`\n**Example**: `!stop 444854`")
        return
    
    # Add command to queue
    await command_queue.put({
        'type': 'stop',
        'teamcode': teamcode,
        'timestamp': datetime.now().isoformat(),
        'user': str(ctx.author)
    })
    
    status_data['last_command'] = f"!stop {teamcode}"
    if teamcode in status_data['active_teams']:
        status_data['active_teams'].remove(teamcode)
    
    embed = discord.Embed(
        title="🛑 Free Fire Bot Stopped",
        description=f"Stopping level-up loop for team **{teamcode}**",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Team Code", value=f"`{teamcode}`", inline=True)
    embed.add_field(name="Requested By", value=ctx.author.mention, inline=True)
    embed.set_footer(text="DHASU-RUSHER Bot")
    
    await ctx.send(embed=embed)
    
    if bot.config['settings']['log_discord_commands']:
        print(f"📨 Discord Command: !stop {teamcode} by {ctx.author}")

@commands.command(name='status')
async def bot_status(ctx):
    """Check bot status and active teams"""
    
    embed = discord.Embed(
        title="📊 Free Fire Bot Status",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Bot Status",
        value="🟢 Online" if status_data['bot_online'] else "🔴 Offline",
        inline=True
    )
    
    embed.add_field(
        name="Active Teams",
        value=f"`{len(status_data['active_teams'])}` teams",
        inline=True
    )
    
    if status_data['active_teams']:
        teams_list = "\n".join([f"• `{team}`" for team in status_data['active_teams']])
        embed.add_field(name="Team Codes", value=teams_list, inline=False)
    
    if status_data['last_command']:
        embed.add_field(
            name="Last Command",
            value=f"`{status_data['last_command']}`",
            inline=False
        )
    
    embed.set_footer(text="DHASU-RUSHER Bot")
    
    await ctx.send(embed=embed)

@commands.command(name='bothelp')
async def help_command(ctx):
    """Show available commands"""
    
    embed = discord.Embed(
        title="🤖 DHASU-RUSHER Bot Commands",
        description="Control your Free Fire bot from Discord!",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="!lw [teamcode]",
        value="Start auto level-up for a team\n**Example**: `!lw 444854`",
        inline=False
    )
    
    embed.add_field(
        name="!stop [teamcode]",
        value="Stop auto level-up for a team\n**Example**: `!stop 444854`",
        inline=False
    )
    
    embed.add_field(
        name="!status",
        value="Check bot status and active teams",
        inline=False
    )
    
    embed.add_field(
        name="!bothelp",
        value="Show this help message",
        inline=False
    )
    
    embed.set_footer(text="DHASU-RUSHER Bot • Made with ❤️")
    
    await ctx.send(embed=embed)

async def run_discord_bot(config):
    """Initialize and run the Discord bot"""
    global bot
    
    bot = DiscordFFBot(config)
    
    # Register commands
    bot.add_command(start_levelup)
    bot.add_command(stop_levelup)
    bot.add_command(bot_status)
    bot.add_command(help_command)
    
    # Start bot
    try:
        print(f"📡 Attempting Discord Login... (Token length: {len(config['discord']['bot_token'])})")
        await bot.start(config['discord']['bot_token'].strip())
    except discord.LoginFailure:
        print("❌ ERROR: Discord Token invalid or improperly formatted!")
        print("   → Please check your Developer Portal for a fresh token.")
    except discord.PrivilegedIntentsRequired:
        print("❌ ERROR: Privileged Intents (Message Content) NOT ENABLED!")
        print("   → Go to Discord Developer Portal > Bot > Privileged Gateway Intents")
        print("   → Enable 'MESSAGE CONTENT INTENT'")
    except Exception as e:
        print(f"❌ Discord Connection Error: {e}")

async def get_command():
    """Get next command from queue (called by main bot)"""
    return await command_queue.get()

def set_bot_status(online: bool):
    """Update bot online status"""
    status_data['bot_online'] = online

if __name__ == "__main__":
    # For testing Discord bot standalone
    config = load_config()
    if config:
        asyncio.run(run_discord_bot(config))
