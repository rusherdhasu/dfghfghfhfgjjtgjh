"""
DHASU-RUSHER Bot Launcher
Runs Discord bot and multiple Free Fire bots from accounts.txt
WITH DYNAMIC RELOAD - Add/Remove accounts without restart!
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import time

# ================= CONFIGURATION =================
# AGAR RENDER PE ENV VARS NAHI CHAL RAHE, TOH YAHAN BHI DAL SAKTE HO:
HARDCODED_TOKEN = "MTQ2OTMzMzI2NDEyNzc1NDU2Ng.G7ckKs.JwoOjuQ0JWkwlPUpFm9hTbN1Wn0bGqYTYUT7f0"          # Paste your Discord Token here
HARDCODED_CHANNEL_ID = "1452134167302373377"     # Paste your Channel ID here
# =================================================

# Environment variables for deployment (Prioritized)
DISCORD_TOKEN = (os.getenv('DISCORD_BOT_TOKEN') or HARDCODED_TOKEN).strip()
DISCORD_CHANNEL = (os.getenv('DISCORD_CHANNEL_ID') or HARDCODED_CHANNEL_ID).strip()
DISCORD_PREFIX = os.getenv('DISCORD_PREFIX', '!')
ACCOUNTS_ENV = os.getenv('ACCOUNTS', '')

# Import both bots
import discord_bot
from main import FreeFireBot

# Import keep-alive for deployment
try:
    from keep_alive import start_health_server
    KEEP_ALIVE_ENABLED = True
except ImportError:
    KEEP_ALIVE_ENABLED = False

# Global tracking
all_bots = {}  # {uid: bot_instance}
bot_tasks = {}  # {uid: task}
accounts_file_path = None
last_modified_time = 0

def load_config():
    """Load configuration from environment variables or config.json"""
    # Try environment variables first (for deployment on Render)
    if DISCORD_TOKEN and DISCORD_CHANNEL:
        print("📡 SUCCESS: Loading config from environment variables.")
        return {
            'discord': {
                'bot_token': DISCORD_TOKEN,
                'command_channel_id': DISCORD_CHANNEL,
                'prefix': DISCORD_PREFIX
            },
            'settings': {
                'auto_reconnect': True,
                'log_discord_commands': True,
                'accounts_file': 'accounts.txt'
            }
        }
    
    # Log what's missing if we can't find env vars
    print("ℹ️  Note: Environment variables (DISCORD_BOT_TOKEN/DISCORD_CHANNEL_ID) not fully set.")
    
    # Fallback to config.json (for local development)
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        print("📁 SUCCESS: Loading config from local config.json.")
        with open(config_path, 'r') as f:
            return json.load(f)
    
    print("❌ CRITICAL ERROR: No configuration found!")
    print("   1. Check if DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID are set in Render Environment Variables.")
    print("   2. For local use, ensure config.json exists in the current directory.")
    return None

def load_accounts():
    """Load accounts from environment variable or accounts.txt"""
    global accounts_file_path
    
    # Try environment variable first (for deployment)
    if ACCOUNTS_ENV:
        print("📡 Loading accounts from environment variable...")
        accounts = {}
        for account_str in ACCOUNTS_ENV.split(','):
            account_str = account_str.strip()
            if ':' in account_str:
                uid, password = account_str.split(':', 1)
                uid = uid.strip()
                accounts[uid] = {'uid': uid, 'password': password.strip()}
        return accounts
    
    # Fallback to accounts.txt (for local development)
    accounts_file_path = os.path.join(os.path.dirname(__file__), 'accounts.txt')
    if os.path.exists(accounts_file_path):
        print("📁 Loading accounts from accounts.txt...")
        accounts = {}
        with open(accounts_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    uid, password = line.split(':', 1)
                    uid = uid.strip()
                    accounts[uid] = {'uid': uid, 'password': password.strip()}
        return accounts
    
    print("❌ Error: No accounts found!")
    print("   Set ACCOUNTS environment variable OR create accounts.txt")
    return {}

def get_file_modified_time():
    """Get last modified time of accounts.txt"""
    global accounts_file_path
    if accounts_file_path and os.path.exists(accounts_file_path):
        return os.path.getmtime(accounts_file_path)
    return 0

async def start_bot(uid, password):
    """Start a single Free Fire bot"""
    print(f"   🟢 Starting bot for UID: {uid}")
    bot = FreeFireBot(uid=uid, password=password)
    all_bots[uid] = bot
    
    # Create task for this bot
    task = asyncio.create_task(
        bot.run_account(),
        name=f"FF Bot {uid}"
    )
    bot_tasks[uid] = task
    return task

async def stop_bot(uid):
    """Stop a single Free Fire bot"""
    if uid in all_bots:
        print(f"   🔴 Stopping bot for UID: {uid}")
        bot = all_bots[uid]
        await bot.stop()
        
        if uid in bot_tasks:
            bot_tasks[uid].cancel()
            del bot_tasks[uid]
        
        del all_bots[uid]

async def account_file_watcher():
    """Watch accounts.txt for changes and reload bots dynamically"""
    global last_modified_time
    
    print("👁️  File watcher started - monitoring accounts.txt for changes...")
    
    while True:
        try:
            await asyncio.sleep(2)  # Check every 2 seconds
            
            current_modified_time = get_file_modified_time()
            
            # File changed?
            if current_modified_time > last_modified_time and last_modified_time > 0:
                print("\n🔄 accounts.txt changed! Reloading accounts...")
                
                # Load new accounts
                new_accounts = load_accounts()
                current_uids = set(all_bots.keys())
                new_uids = set(new_accounts.keys())
                
                # Find accounts to add
                to_add = new_uids - current_uids
                # Find accounts to remove
                to_remove = current_uids - new_uids
                
                # Remove old accounts
                for uid in to_remove:
                    await stop_bot(uid)
                
                # Add new accounts
                for uid in to_add:
                    account = new_accounts[uid]
                    await start_bot(account['uid'], account['password'])
                
                if to_add or to_remove:
                    print(f"✅ Reload complete! Added: {len(to_add)}, Removed: {len(to_remove)}")
                    print(f"📊 Total active bots: {len(all_bots)}")
                else:
                    print("ℹ️  No changes detected in accounts")
            
            last_modified_time = current_modified_time
            
        except Exception as e:
            print(f"⚠️  File watcher error: {e}")
            await asyncio.sleep(5)

def print_banner():
    """Print startup banner"""
    print("=" * 60)
    print("🤖 DHASU-RUSHER BOT LAUNCHER (Dynamic Reload)")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

async def main():
    """Main launcher function"""
    global last_modified_time
    
    print_banner()
    
    # Start health check server for deployment (keeps Render alive)
    if KEEP_ALIVE_ENABLED:
        port = int(os.getenv('PORT', 8080))
        start_health_server(port)
    
    # Load configuration
    config = load_config()
    if not config:
        return
    
    # Validate configuration
    if config['discord']['bot_token'] == "YOUR_DISCORD_BOT_TOKEN_HERE" or not config['discord']['bot_token']:
        print("❌ Error: Discord bot token is missing!")
        return
    
    if config['discord']['command_channel_id'] == "YOUR_CHANNEL_ID_HERE" or not config['discord']['command_channel_id']:
        print("❌ Error: Discord channel ID is missing!")
        return

    # Create Discord bot task (START THIS FIRST)
    print("🤖 Starting Discord bot...")
    discord_task = asyncio.create_task(
        discord_bot.run_discord_bot(config),
        name="Discord Bot"
    )
    
    # Load accounts
    accounts = load_accounts()
    if not accounts:
        print("ℹ️  Note: No accounts found yet. Waiting for accounts.txt or ACCOUNTS env var...")
    
    # Set initial file modified time
    last_modified_time = get_file_modified_time()
    
    print(f"\n📋 Configuration loaded successfully!")
    print(f"   Discord Channel ID: {config['discord']['command_channel_id']}")
    print(f"   Total Accounts: {len(accounts)}")
    print()
    
    # Create bot instances for all accounts
    if accounts:
        print("🚀 Starting Free Fire bots...\n")
        for idx, (uid, account) in enumerate(accounts.items(), 1):
            print(f"   [{idx}] Creating bot for UID: {uid}")
            await start_bot(account['uid'], account['password'])
    
    # Create file watcher task
    watcher_task = asyncio.create_task(
        account_file_watcher(),
        name="File Watcher"
    )
    
    print(f"\n✅ All components initialized!")
    print("━" * 60)
    print("📢 Commands available in Discord:")
    print("   /lw [teamcode]  - Start level-up")
    print("   /stop [teamcode] - Stop level-up")
    print("   /status - Check bot status")
    print("   /bothelp - Show help")
    print("━" * 60)
    
    if os.getenv('RENDER'):
        print("🚀 RUNNING ON RENDER.COM")
        print(f"🔗 Health Link: https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/health")
    else:
        print("🔄 Dynamic Reload ENABLED (Local Mode)")
        print("   → Add account to accounts.txt = Auto start")
        print("   → Remove account = Auto stop")
    
    print("━" * 60)
    print("\n⚠️  Bot is now running. Press Ctrl+C to stop.\n")
    
    try:
        # Run Discord bot, file watcher, and all FF bots concurrently
        all_tasks = [discord_task, watcher_task] + list(bot_tasks.values())
        
        print(f"⌛ Monitoring {len(all_tasks)} active tasks...")
        
        # Use wait to catch exceptions early
        done, pending = await asyncio.wait(all_tasks, return_when=asyncio.FIRST_EXCEPTION)
        
        for task in done:
            if task.exception():
                print(f"❌ CRITICAL ERROR in task '{task.get_name()}': {task.exception()}")
                # Try to get more detail
                import traceback
                traceback.print_exception(type(task.exception()), task.exception(), task.exception().__traceback__)
        
    except Exception as e:
        print(f"❌ Main Loop Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🛑 Shutdown initiated...")
        discord_task.cancel()
        watcher_task.cancel()
        for uid in list(all_bots.keys()):
            await stop_bot(uid)
        print("✅ Cleanup complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")



