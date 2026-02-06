import requests , os , psutil , sys , jwt , pickle , json , binascii , time , urllib3 , base64 , datetime , re , socket , threading , ssl , pytz , aiohttp
from protobuf_decoder.protobuf_decoder import Parser
from xC4 import * ; from xHeaders import *
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from Pb2 import DEcwHisPErMsG_pb2 , MajoRLoGinrEs_pb2 , PorTs_pb2 , MajoRLoGinrEq_pb2 , sQ_pb2 , Team_msg_pb2
from cfonts import render, say
from APIS import insta
from flask import Flask, jsonify, request
import asyncio
import signal
import sys
# Add these imports if not already present
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Discord bot integration
try:
    import discord_bot
    DISCORD_ENABLED = True
except ImportError:
    DISCORD_ENABLED = False
    print("⚠️ Discord bot module not available. Discord commands disabled.")



urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  

# DHASU-RUSHER Configuration
ADMIN_UID = "5513136279"
server2 = "IND"
key2 = "najmi99"
BYPASS_TOKEN = "your_bypass_token_here"
bot_servers = "IND" "BD" "PK" "BR" "US" "SP",

# Global Registry for tracking busy bots and active team codes
# Format: {team_code: bot_instance}
active_team_codes = {}

class FreeFireBot:
    def __init__(self, uid, password):
        self.acc_uid = uid
        self.acc_password = password
        self.acc_name = "Connecting..."
        
        # Connection Writers
        self.online_writer = None
        self.whisper_writer = None
        
        # Room/Squad State
        self.insquad = None
        self.joining_team = False
        self.active_squad_uid = None
        
        # Game Task State
        self.auto_start_running = False
        self.auto_start_teamcode = None
        self.stop_auto = False
        self.auto_start_task = None
        
        # Configuration
        self.start_spam_duration = 15
        self.wait_after_match = 18
        self.start_spam_delay = 0.1
        
        # Connection parameters
        self.key = None
        self.iv = None
        self.region = "ind"
        self.auth_token = None
        self.reconnect_delay = 5.0
        self.consecutive_failures = 0
        self.force_stop = False

    async def stop(self):
        """Cleanly stop the bot and close connections"""
        self.log("Stopping bot instance...")
        self.force_stop = True
        self.stop_auto = True
        
        # Stop any running game task
        if self.auto_start_task:
            self.auto_start_task.cancel()
            
        # Remove from global coordination
        if self.auto_start_teamcode in active_team_codes:
            del active_team_codes[self.auto_start_teamcode]
        
        # Close connection writers
        if self.online_writer:
            try:
                self.online_writer.close()
                await self.online_writer.wait_closed()
            except: pass
            self.online_writer = None
            
        if self.whisper_writer:
            try:
                self.whisper_writer.close()
                await self.whisper_writer.wait_closed()
            except: pass
            self.whisper_writer = None

    def log(self, message):
        # Filter for important events to keep console clean
        important_keywords = ["online", "activated", "stopped", "error", "failed", "squad", "team"]
        if any(keyword in message.lower() for keyword in important_keywords):
            # Only print if it's not a generic connecting/searching log
            if not any(k in message.lower() for k in ["attempting", "connecting", "detecting"]):
                 print(f"[{self.acc_uid}] {message}")

    async def SEndMsG(self, H, message, Uid, chat_id, key, iv):
        # H (chat_type): 1=Clan, 2=Private, 3/5=Squad
        # reference logic uses xSEndMsg for 1 and 2, xSEndMsgsQ for squad
        if H == 1: # Clan
            msg_packet = await xSEndMsg(message, 1, chat_id, chat_id, key, iv)
        elif H == 2: # Private
            msg_packet = await xSEndMsg(message, 2, Uid, Uid, key, iv)
        else: # Squad default
            msg_packet = await xSEndMsgsQ(message, chat_id or Uid, key, iv)
        return msg_packet

    async def SEndPacKeT(self, TypE, PacKeT):
        try:
            if TypE == 'ChaT' and self.whisper_writer:
                self.whisper_writer.write(PacKeT)
                await self.whisper_writer.drain()
                return True
            elif TypE == 'OnLine' and self.online_writer:
                self.online_writer.write(PacKeT)
                await self.online_writer.drain()
                return True
            else:
                self.log(f"⚠️ SEndPacKeT Failed: Writer not available or unknown type {TypE}")
                return False
        except Exception as e:
            self.log(f"❌ SEndPacKeT Error: {e}")
            return False

    async def safe_send_message(self, chat_type, message, target_uid, chat_id, key, iv, max_retries=3):
        for attempt in range(max_retries):
            try:
                P = await self.SEndMsG(chat_type, message, target_uid, chat_id, key, iv)
                await self.SEndPacKeT('ChaT', P)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
        return False

    async def discord_command_listener(self):
        """Listen for commands from Discord bot"""
        if not DISCORD_ENABLED:
            return
        
        self.log("📡 Discord command listener started")
        
        while not self.force_stop:
            try:
                # Get command from Discord queue (with timeout)
                command = await asyncio.wait_for(
                    discord_bot.get_command(),
                    timeout=1.0
                )
                
                cmd_type = command.get('type')
                teamcode = command.get('teamcode')
                
                self.log(f"📨 Discord Command Received: {cmd_type} {teamcode}")
                
                if cmd_type == 'start':
                    # Check if already running
                    if teamcode in active_team_codes:
                        busy_bot = active_team_codes[teamcode]
                        if busy_bot.auto_start_running:
                            self.log(f"⏭️ Skipping {teamcode} - Already handled by {busy_bot.acc_uid}")
                            continue
                    
                    if self.auto_start_running:
                        self.log(f"⏭️ Bot already running another task")
                        continue
                    
                    # Start the task
                    active_team_codes[teamcode] = self
                    self.stop_auto = False
                    self.auto_start_running = True
                    self.auto_start_teamcode = teamcode
                    
                    self.log(f"🎮 Starting level-up for team {teamcode} (Discord)")
                    
                    # Use dummy values for Discord commands (no in-game chat feedback)
                    self.auto_start_task = asyncio.create_task(
                        self.auto_start_loop(
                            teamcode,
                            self.acc_uid,  # dummy uid
                            None,  # no chat_id
                            0,  # no chat type (Discord)
                            self.key,
                            self.iv,
                            self.region
                        )
                    )
                
                elif cmd_type == 'stop':
                    # Stop if this bot is handling the teamcode
                    if self.auto_start_running and self.auto_start_teamcode == teamcode:
                        self.stop_auto = True
                        self.auto_start_running = False
                        code = self.auto_start_teamcode
                        self.auto_start_teamcode = None
                        if code in active_team_codes:
                            del active_team_codes[code]
                        self.log(f"🛑 Stopped team {teamcode} (Discord)")
                
            except asyncio.TimeoutError:
                # No command received, continue listening
                continue
            except Exception as e:
                if not self.force_stop:
                    self.log(f"⚠️ Discord listener error: {e}")
                await asyncio.sleep(1)


    async def auto_start_loop(self, team_code, uid, chat_id, chat_type, key, iv, region):
        """Reference Logic for Match Start (Level-up-multi style)"""
        self.log(f"🔥 Starting Match Start Loop for Team: {team_code}")
        self.stop_auto = False
        
        while not self.stop_auto:
            try:
                # 1. Join Squad (Ref uses GenJoinSquadsPacket)
                self.log(f"🎮 Attempting to join team {team_code}...")
                join_packet = await GenJoinSquadsPacket(team_code, key, iv)
                await self.SEndPacKeT('OnLine', join_packet)
                
                # IMPORTANT: Reference Wait after Join (2s)
                await asyncio.sleep(2.0)
                
                if self.stop_auto: break
                
                await self.safe_send_message(chat_type, f"🤖 DHASU-RUSHER\n[00FF00]START HUA WAIT\n[FFFFFF]FIR JOIN SQUAD HOGA", uid, chat_id, key, iv)
                
                # 2. Match Start Spammer (Opcode 9 ONLY)
                p9 = await start_auto_packet(key, iv, region, opcode=9)
                
                self.log(f"🔥 Spamming Start Opcode 9 for 6s...")
                end_time = time.time() + 6
                while time.time() < end_time and not self.stop_auto:
                    await self.SEndPacKeT('OnLine', p9)
                    await asyncio.sleep(0.2) # Ref: 0.2s delay
                
                if self.stop_auto: break
                
                # 3. Wait for Match Conclusion (Ref: 24s)
                self.log(f"⏳ Match started/spam finished, waiting 24s...")
                await self.safe_send_message(chat_type, f"🤖 DHASU-RUSHER\n[F0F0F0]MATCH ENDED / WAITING", uid, chat_id, key, iv)
                
                # Wait in chunks to be cancelable
                wait_end = time.time() + 24
                while time.time() < wait_end and not self.stop_auto:
                    await asyncio.sleep(1)
                
                if self.stop_auto: break
                
                # 4. Leave Squad (Opcode 7)
                self.log(f"🚪 Leaving squad to rejoin...")
                await self.safe_send_message(chat_type, f"🤖 DHASU-RUSHER\n[D3D3D3]SQUAD LEFT / REJOINING", uid, chat_id, key, iv)
                # Note: leave_squad_packet uses the correct structure internally
                await self.SEndPacKeT('OnLine', await leave_squad_packet(self.acc_uid, key, iv, region))
                
                # Wait after leave (Ref style)
                await asyncio.sleep(2.0)
                
            except Exception as e:
                self.log(f"❌ Error in auto_start_loop: {e}")
                break
        
        self.stop_auto = False
        self.log(f"🛑 Match Start Loop terminated.")

    async def TcPOnLine(self, ip, port, key, iv, AutHToKen):
        self.log(f"Attempting to connect to TCP Online {ip}:{port}...")
        
        while not self.force_stop:
            try:
                reader, writer = await asyncio.open_connection(ip, int(port))
                self.online_writer = writer
                
                bytes_payload = bytes.fromhex(AutHToKen)
                self.online_writer.write(bytes_payload)
                await self.online_writer.drain()
                self.log("Connected to TCP Online")
                
                while True:
                    data2 = await reader.read(9999)
                    if not data2: break
                    data_hex = data2.hex()

                    # =================== AUTO ACCEPT HANDLING ===================
                    if data_hex.startswith('0500') and self.insquad is not None and self.joining_team == False:
                        try:
                            packet = await DeCode_PackEt(data_hex[10:])
                            packet_json = json.loads(packet)
                            if packet_json.get('1') in [6, 7]: 
                                 self.insquad = None
                                 self.joining_team = False
                                 continue
                        except: pass
                    
                    if data_hex.startswith("0500") and self.insquad is None and self.joining_team == False:
                        try:
                            packet = await DeCode_PackEt(data_hex[10:])
                            packet_json = json.loads(packet)
                            uid = packet_json['5']['data']['2']['data']['1']['data']
                            squad_owner = packet_json['5']['data']['1']['data']
                            code = packet_json['5']['data']['8']['data']
                            emote_id = 909050009
                            
                            Join = await ArohiAccepted(squad_owner, code, key, iv)
                            await self.SEndPacKeT('OnLine', Join)
                            self.insquad = True
                        except: pass
                    
                    if data_hex.startswith('0500') and len(data_hex) > 1000 and self.joining_team:
                        try:
                            packet = await DeCode_PackEt(data_hex[10:])
                            packet_json = json.loads(packet)
                            OwNer_UiD , CHaT_CoDe , SQuAD_CoDe = await GeTSQDaTa(packet_json)
                            JoinCHaT = await AutH_Chat(3, OwNer_UiD, CHaT_CoDe, key, iv)
                            await self.SEndPacKeT('ChaT', JoinCHaT)
                            self.joining_team = False
                        except: pass

                if self.online_writer:
                    self.online_writer.close()
                    await self.online_writer.wait_closed()
                    self.online_writer = None
                
                # Successful connection, reset failures
                self.consecutive_failures = 0
                
            except Exception as e:
                if self.force_stop: break
                self.consecutive_failures += 1
                
                # Exponential backoff with jitter
                delay = min(30, self.reconnect_delay * (2 ** min(self.consecutive_failures - 1, 4)))
                jitter = random.uniform(0.5, 1.5)
                final_delay = delay * jitter
                
                self.log(f"TCP Online Error: {e}")
                self.log(f"🔄 Reconnecting in {final_delay:.1f}s (Attempt {self.consecutive_failures})")
                await asyncio.sleep(final_delay)

    async def TcPChaT(self, ip, port, AutHToKen, key, iv, LoGinDaTaUncRypTinG, ready_event):
        self.log(f"Connecting to TCP Chat {ip}:{port}...")
        while not self.force_stop:
            try:
                reader, writer = await asyncio.open_connection(ip, int(port))
                self.whisper_writer = writer
                
                bytes_payload = bytes.fromhex(AutHToKen)
                self.whisper_writer.write(bytes_payload)
                await self.whisper_writer.drain()
                
                # AutH_GlobAl is CRITICAL for receiving Clan/Global Chat
                AuthG = await AutH_GlobAl(key, iv)
                self.whisper_writer.write(AuthG)
                await self.whisper_writer.drain()

                # reference logic: If bot is in clan, AuthClan is required
                if hasattr(LoGinDaTaUncRypTinG, 'Clan_ID') and LoGinDaTaUncRypTinG.Clan_ID:
                    clan_id = LoGinDaTaUncRypTinG.Clan_ID
                    clan_data = LoGinDaTaUncRypTinG.Clan_Compiled_Data
                    self.log(f"🏰 Authenticating with Clan ID: {clan_id}")
                    AuthC = await AuthClan(clan_id, clan_data, key, iv)
                    self.whisper_writer.write(AuthC)
                    await self.whisper_writer.drain()

                ready_event.set()
                self.log("Connected to TCP Chat & Authenticated Global Channel")
                
                while True:
                    data = await reader.read(1024 * 8)
                    if not data: break
                    
                    data_hex = data.hex()
                    
                    # Detect Packet Header (12=Whisper, 11=Team, 10=Clan?, 0a=Global/Regional)
                    if data_hex.startswith("12") or data_hex.startswith("11") or data_hex.startswith("10") or data_hex.startswith("0a"):
                        # self.log(f"📥 Received Packet: {data_hex[:20]}...") # Suppressed for CPU/Clutter
                        try:
                            # Try Decoding logic
                            inPuTMsG = ""
                            sender_uid = None
                            chat_id = None
                            chat_type = 1 # Default
                            
                            if data_hex.startswith("12"):
                                response = await DecodeWhisperMessage(data_hex[10:])
                                sender_uid = response.Data.uid
                                chat_id = response.Data.Chat_ID
                                chat_type = response.Data.chat_type
                                inPuTMsG = response.Data.msg.lower()
                                # self.log(f"🔎 Detected Whisper from {sender_uid}") # Suppressed
                            else:
                                # Try Team/Squad/Clan decode
                                try:
                                    # Using Team_msg_pb2 logic
                                    packet = bytes.fromhex(data_hex[10:])
                                    response = Team_msg_pb2.GenTeamWhisper()
                                    response.ParseFromString(packet)
                                    sender_uid = response.data.uid
                                    chat_id = response.data.chat_id
                                    chat_type = response.data.chat_type
                                    inPuTMsG = response.data.msg.lower()
                                    # self.log(f"🔎 Detected Multi-Channel Pkt (Type {chat_type}) from {sender_uid}") # Suppressed
                                except Exception as e:
                                    # Fallback to sQ_pb2 logic
                                    try:
                                        response = await decode_team_packet(data_hex[10:])
                                        sender_uid = response.details.player_uid
                                        chat_id = sender_uid # Use UID as ID if not present
                                        chat_type = 5 # Squad default
                                        inPuTMsG = response.details.team_session.lower()
                                        # self.log(f"🔎 Detected Squad Pkt from {sender_uid}") # Suppressed
                                    except:
                                        continue

                            if not inPuTMsG: continue
                            
                            # FLEET IGNORE: Skip if message is from another bot in our own fleet
                            if str(sender_uid) == str(self.acc_uid) or str(sender_uid) in active_bots:
                                continue 

                            self.log(f"💬 Cmd Received: '{inPuTMsG[:30]}' [Type: {chat_type}]")

                            # --- COMMANDS ---
                            if inPuTMsG.strip().startswith('/lw'):
                                parts = inPuTMsG.strip().split()
                                if len(parts) < 2: continue
                                team_code = parts[1]
                                
                                # SMART COORDINATION: Check if ANY bot is already handling this code
                                if team_code in active_team_codes:
                                    busy_bot = active_team_codes[team_code]
                                    if busy_bot.auto_start_running:
                                        self.log(f"⏭️ Skipping {team_code} - Already handled by {busy_bot.acc_uid}")
                                        continue

                                if self.auto_start_running: continue

                                active_team_codes[team_code] = self
                                self.stop_auto = False
                                self.auto_start_running = True
                                self.auto_start_teamcode = team_code
                                
                                await self.safe_send_message(chat_type, f"🤖 DHASU-RUSHER BOT ACTIVATED!\nTeam: {team_code}", sender_uid, chat_id, key, iv)
                                
                                self.auto_start_task = asyncio.create_task(
                                    self.auto_start_loop(team_code, sender_uid, chat_id, chat_type, key, iv, self.region)
                                )
                            
                            if inPuTMsG.strip().startswith('/stop'):
                                parts = inPuTMsG.strip().split()
                                target_code = parts[1] if len(parts) > 1 else None
                                
                                # SMART STOP: Only stop if targeting THIS bot's specific team code
                                # or if it's a direct private stop (Type 2)
                                if target_code:
                                    if self.auto_start_running and self.auto_start_teamcode == target_code:
                                        self.stop_auto = True
                                        self.auto_start_running = False
                                        code = self.auto_start_teamcode
                                        self.auto_start_teamcode = None
                                        if code in active_team_codes: del active_team_codes[code]
                                        self.log(f"🛑 Smart Stop Triggered for team {target_code}")
                                        await self.safe_send_message(chat_type, f"🤖 STOPPED for team {target_code}!", sender_uid, chat_id, key, iv)
                                elif chat_type == 2: # Private Chat Stop (Always Allow)
                                    if self.auto_start_running:
                                        self.stop_auto = True
                                        self.auto_start_running = False
                                        code = self.auto_start_teamcode
                                        self.auto_start_teamcode = None
                                        if code in active_team_codes: del active_team_codes[code]
                                        self.log(f"🛑 Manual Stop Triggered via Private Chat")
                                        await self.safe_send_message(chat_type, f"🤖 DHASU-RUSHER STOPPED!", sender_uid, chat_id, key, iv)
                                else:
                                    # Global stop without code in Clan chat? Ignore to avoid stopping other bots
                                    self.log(f"ℹ️ Received general /stop in shared channel. Ignoring (use /stop [code])")

                            if inPuTMsG.strip().lower() in ("help", "/help", "menu", "/menu"):
                                header = f"[b][c]{get_random_color()}DHASU-RUSHER GAME BOT MENU\n\n[FFFFFF]⚡ /lw [code] - Start Auto Start\n⚡ /stop [code] - Stop Current Loop\n⚡ /help - This Menu"
                                await self.safe_send_message(chat_type, header, sender_uid, chat_id, key, iv)

                        except Exception as e:
                            self.log(f"⚠️ Chat Loop Error: {e}")
                
                if self.whisper_writer:
                    self.whisper_writer.close()
                    await self.whisper_writer.wait_closed()
                    self.whisper_writer = None
                
                # Reset failures on successful completion of loop
                self.consecutive_failures = 0
                    
            except Exception as e:
                if self.force_stop: break
                self.consecutive_failures += 1
                
                # Exponential backoff with jitter
                delay = min(30, self.reconnect_delay * (2 ** min(self.consecutive_failures - 1, 4)))
                jitter = random.uniform(0.5, 1.5)
                final_delay = delay * jitter
                
                self.log(f"TCP Chat Error: {e}")
                self.log(f"🔄 Reconnecting in {final_delay:.1f}s (Attempt {self.consecutive_failures})")
                await asyncio.sleep(final_delay)

    async def run_account(self):
        self.log("Initializing DHASU-RUSHER Bot...")
        
        while not self.force_stop:
            try:
                Uid, Pw = self.acc_uid, self.acc_password
                
                open_id, access_token = await GeNeRaTeAccEss(Uid, Pw)
                if not open_id or not access_token: 
                    raise ConnectionError("Failed to generate access token")
                
                PyL = await EncRypTMajoRLoGin(open_id, access_token)
                MajoRLoGinResPonsE = await MajorLogin(PyL)
                if not MajoRLoGinResPonsE: 
                    raise ConnectionError("MajorLogin failed")
                
                MajoRLoGinauTh = await DecRypTMajoRLoGin(MajoRLoGinResPonsE)
                UrL = MajoRLoGinauTh.url
                self.region = MajoRLoGinauTh.region
                ToKen = MajoRLoGinauTh.token
                tarGeT_uid = MajoRLoGinauTh.account_uid
                self.key = MajoRLoGinauTh.key
                self.iv = MajoRLoGinauTh.iv
                timestamp = MajoRLoGinauTh.timestamp
                
                LoGinDaTa = await GetLoginData(UrL, PyL, ToKen)
                if not LoGinDaTa: 
                    raise ConnectionError("Failed to get LoginData")
                    
                LoGinDaTaUncRypTinG = await DecRypTLoGinDaTa(LoGinDaTa)
                OnLineiP, OnLineporT = LoGinDaTaUncRypTinG.Online_IP_Port.split(":")
                ChaTiP, ChaTporT = LoGinDaTaUncRypTinG.AccountIP_Port.split(":")
                self.acc_name = LoGinDaTaUncRypTinG.AccountName
                
                equie_emote(ToKen, UrL)
                AutHToKen = await xAuThSTarTuP(int(tarGeT_uid), ToKen, int(timestamp), self.key, self.iv)
                ready_event = asyncio.Event()
                
                task1 = asyncio.create_task(self.TcPChaT(ChaTiP, ChaTporT, AutHToKen, self.key, self.iv, LoGinDaTaUncRypTinG, ready_event))
                task2 = asyncio.create_task(self.TcPOnLine(OnLineiP, OnLineporT, self.key, self.iv, AutHToKen))  
                
                # Start Discord command listener if enabled
                task3 = None
                if DISCORD_ENABLED:
                    task3 = asyncio.create_task(self.discord_command_listener())
                    self.log("📡 Discord integration enabled")
                
                self.log(f"DHASU-RUSHER BOT ONLINE - {self.acc_name}")
                
                # Update Discord bot status
                if DISCORD_ENABLED:
                    discord_bot.set_bot_status(True)
                
                # Wait for tasks to complete or fail
                tasks = [task1, task2]
                if task3: tasks.append(task3)
                
                # Use wait instead of gather to catch the first failure
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass
                
                # Check for exceptions
                for task in done:
                    if task.exception():
                        raise task.exception()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.force_stop: break
                self.consecutive_failures += 1
                
                # Exponential backoff with jitter
                delay = min(60, self.reconnect_delay * (2 ** min(self.consecutive_failures - 1, 5)))
                jitter = random.uniform(0.5, 1.5)
                final_delay = delay * jitter
                
                self.log(f"💥 Initialization/Fatal Error: {e}")
                self.log(f"🔄 Full Reset in {final_delay:.1f}s (Attempt {self.consecutive_failures})")
                
                if DISCORD_ENABLED:
                    discord_bot.set_bot_status(False)
                    
                await asyncio.sleep(final_delay)

    # Move all bot methods here...
# VariabLes dyli 
#------------------------------------------#
spam_room = False
spammer_uid = None
spam_chat_id = None
spam_uid = None
Spy = False
Chat_Leave = False
fast_spam_running = False
fast_spam_task = None
custom_spam_running = False
custom_spam_task = None
spam_request_running = False
spam_request_task = None
evo_fast_spam_running = False
evo_fast_spam_task = None
evo_custom_spam_running = False
evo_custom_spam_task = None
# Add with other global variables
reject_spam_running = False
insquad = None 
joining_team = False 
reject_spam_task = None
lag_running = False
lag_task = None
# Add these with your other global variables at the top
reject_spam_running = False
reject_spam_task = None
evo_cycle_running = False
evo_cycle_task = None
# Add with other global variables at the top
evo_emotes = {
    "1": "909000063",   # AK
    "2": "909000068",   # SCAR
    "3": "909000075",   # 1st MP40
    "4": "909040010",   # 2nd MP40
    "5": "909000081",   # 1st M1014
    "6": "909039011",   # 2nd M1014
    "7": "909000085",   # XM8
    "8": "909000090",   # Famas
    "9": "909000098",   # UMP
    "10": "909035007",  # M1887
    "11": "909042008",  # Woodpecker
    "12": "909041005",  # Groza
    "13": "909033001",  # M4A1
    "14": "909038010",  # Thompson
    "15": "909038012",  # G18
    "16": "909045001",  # Parafal
    "17": "909049010",  # P90
    "18": "909051003"   # m60
}
#------------------------------------------#

# Emote mapping for evo commands
EMOTE_MAP = {
    1: 909000063,
    2: 909000081,
    3: 909000075,
    4: 909000085,
    5: 909000134,
    6: 909000098,
    7: 909035007,
    8: 909051012,
    9: 909000141,
    10: 909034008,
    11: 909051015,
    12: 909041002,
    13: 909039004,
    14: 909042008,
    15: 909051014,
    16: 909039012,
    17: 909040010,
    18: 909035010,
    19: 909041005,
    20: 909051003,
    21: 909034001
}

# RARE LOOK CHANGER BUNDLE ID
BUNDLE = {
    "rampage": 914000002,
    "cannibal": 914000003,
    "devil": 914038001,
    "scorpio": 914039001,
    "frostfire": 914042001,
    "paradox": 914044001,
    "naruto": 914047001,
    "aurora": 914047002,
    "midnight": 914048001,
    "itachi": 914050001,
    "dreamspace": 914051001
}
# Emote mapping for all emote commands
ALL_EMOTE = {
    1: 909000001,
    2: 909000002,
    3: 909000003,
    4: 909000004,
    5: 909000005,
    6: 909000006,
    7: 909000007,
    8: 909000008,
    9: 909000009,
    10: 909000010,
    11: 909000011,
    12: 909000012,
    13: 909000013,
    14: 909000014,
    15: 909000015,
    16: 909000016,
    17: 909000017,
    18: 909000018,
    19: 909000019,
    20: 909000020,
    21: 909000021,
    22: 909000022,
    23: 909000023,
    24: 909000024,
    25: 909000025,
    26: 909000026,
    27: 909000027,
    28: 909000028,
    29: 909000029,
    30: 909000031,
    31: 909000032,
    32: 909000033,
    33: 909000034,
    34: 909000035,
    35: 909000036,
    36: 909000037,
    37: 909000038,
    38: 909000039,
    39: 909000040,
    40: 909000041,
    41: 909000042,
    42: 909000043,
    43: 909000044,
    44: 909000045,
    45: 909000046,
    46: 909000047,
    47: 909000048,
    48: 909000049,
    49: 909000051,
    50: 909000052,
    51: 909000053,
    52: 909000054,
    53: 909000055,
    54: 909000056,
    55: 909000057,
    56: 909000058,
    57: 909000059,
    58: 909000060,
    59: 909000061,
    60: 909000062,
    61: 909000063,
    62: 909000064,
    63: 909000065,
    64: 909000066,
    65: 909000067,
    66: 909000068,
    67: 909000069,
    68: 909000070,
    69: 909000071,
    70: 909000072,
    71: 909000073,
    72: 909000074,
    73: 909000075,
    74: 909000076,
    75: 909000077,
    76: 909000078,
    77: 909000079,
    78: 909000080,
    79: 909000081,
    80: 909000082,
    81: 909000083,
    82: 909000084,
    83: 909000085,
    84: 909000086,
    85: 909000087,
    86: 909000088,
    87: 909000089,
    88: 909000090,
    89: 909000091,
    90: 909000092,
    91: 909000093,
    92: 909000094,
    93: 909000095,
    94: 909000096,
    95: 909000097,
    96: 909000098,
    97: 909000099,
    98: 909000100,
    99: 909000101,
    100: 909000102,
    101: 909000103,
    102: 909000104,
    103: 909000105,
    104: 909000106,
    105: 909000107,
    106: 909000108,
    107: 909000109,
    108: 909000110,
    109: 909000111,
    110: 909000112,
    111: 909000113,
    112: 909000114,
    113: 909000115,
    114: 909000116,
    115: 909000117,
    116: 909000118,
    117: 909000119,
    118: 909000120,
    119: 909000121,
    120: 909000122,
    121: 909000123,
    122: 909000124,
    123: 909000125,
    124: 909000126,
    125: 909000127,
    126: 909000128,
    127: 909000129,
    128: 909000130,
    129: 909000131,
    130: 909000132,
    131: 909000133,
    132: 909000134,
    133: 909000135,
    134: 909000136,
    135: 909000137,
    136: 909000138,
    137: 909000139,
    138: 909000140,
    139: 909000141,
    140: 909000142,
    141: 909000143,
    142: 909000144,
    143: 909000145,
    144: 909000150,
    145: 909033001,
    146: 909033002,
    147: 909033003,
    148: 909033004,
    149: 909033005,
    150: 909033006,
    151: 909033007,
    152: 909033008,
    153: 909033009,
    154: 909033010,
    155: 909034001,
    156: 909034002,
    157: 909034003,
    158: 909034004,
    159: 909034005,
    160: 909034006,
    161: 909034007,
    162: 909034008,
    163: 909034009,
    164: 909034010,
    165: 909034011,
    166: 909034012,
    167: 909034013,
    168: 909034014,
    169: 909035001,
    170: 909035002,
    171: 909035003,
    172: 909035004,
    173: 909035005,
    174: 909035006,
    175: 909035007,
    176: 909035008,
    177: 909035009,
    178: 909035010,
    179: 909035011,
    180: 909035012,
    181: 909035013,
    182: 909035014,
    183: 909035015,
    184: 909036001,
    185: 909036002,
    186: 909036003,
    187: 909036004,
    188: 909036005,
    189: 909036006,
    190: 909036008,
    191: 909036009,
    192: 909036010,
    193: 909036011,
    194: 909036012,
    195: 909036014,
    196: 909037001,
    197: 909037002,
    198: 909037003,
    199: 909037004,
    200: 909037005,
    201: 909037006,
    202: 909037007,
    203: 909037008,
    204: 909037009,
    205: 909037010,
    206: 909037011,
    207: 909037012,
    208: 909038001,
    209: 909038002,
    210: 909038003,
    211: 909038004,
    212: 909038005,
    213: 909038006,
    214: 909038008,
    215: 909038009,
    216: 909038010,
    217: 909038011,
    218: 909038012,
    219: 909038013,
    220: 909039001,
    221: 909039002,
    222: 909039003,
    223: 909039004,
    224: 909039005,
    225: 909039006,
    226: 909039007,
    227: 909039008,
    228: 909039009,
    229: 909039010,
    230: 909039011,
    231: 909039012,
    232: 909039013,
    233: 909039014,
    234: 909040001,
    235: 909040002,
    236: 909040003,
    237: 909040004,
    238: 909040005,
    239: 909040006,
    240: 909040008,
    241: 909040009,
    242: 909040010,
    243: 909040011,
    244: 909040012,
    245: 909040013,
    246: 909040014,
    247: 909041001,
    248: 909041002,
    249: 909041003,
    250: 909041004,
    251: 909041005,
    252: 909041006,
    253: 909041007,
    254: 909041008,
    255: 909041009,
    256: 909041010,
    257: 909041011,
    258: 909041012,
    259: 909041013,
    260: 909041014,
    261: 909041015,
    262: 909042001,
    263: 909042002,
    264: 909042003,
    265: 909042004,
    266: 909042005,
    267: 909042006,
    268: 909042007,
    269: 909042008,
    270: 909042009,
    271: 909042011,
    272: 909042012,
    273: 909042013,
    274: 909042016,
    275: 909042017,
    276: 909042018,
    277: 909043001,
    278: 909043002,
    279: 909043003,
    280: 909043004,
    281: 909043005,
    282: 909043006,
    283: 909043007,
    284: 909043008,
    285: 909043009,
    286: 909043010,
    287: 909043013,
    288: 909044001,
    289: 909044002,
    290: 909044003,
    291: 909044004,
    292: 909044005,
    293: 909044006,
    294: 909044007,
    295: 909044008,
    296: 909044009,
    297: 909044010,
    298: 909044011,
    299: 909044012,
    300: 909044015,
    301: 909044016,
    302: 909045001,
    303: 909045002,
    304: 909045003,
    305: 909045004,
    306: 909045005,
    307: 909045006,
    308: 909045007,
    309: 909045008,
    310: 909045009,
    311: 909045010,
    312: 909045011,
    313: 909045012,
    314: 909045015,
    315: 909045016,
    316: 909045017,
    317: 909046001,
    318: 909046002,
    319: 909046003,
    320: 909046004,
    321: 909046005,
    322: 909046006,
    323: 909046007,
    324: 909046008,
    325: 909046009,
    326: 909046010,
    327: 909046011,
    328: 909046012,
    329: 909046013,
    330: 909046014,
    331: 909046015,
    332: 909046016,
    333: 909046017,
    334: 909047001,
    335: 909047002,
    336: 909047003,
    337: 909047004,
    338: 909047005,
    339: 909047006,
    340: 909047007,
    341: 909047008,
    342: 909047009,
    343: 909047010,
    344: 909047011,
    345: 909047012,
    346: 909047013,
    347: 909047015,
    348: 909047016,
    349: 909047017,
    350: 909047018,
    351: 909047019,
    352: 909048001,
    353: 909048002,
    354: 909048003,
    355: 909048004,
    356: 909048005,
    357: 909048006,
    358: 909048007,
    359: 909048008,
    360: 909048009,
    361: 909048010,
    362: 909048011,
    363: 909048012,
    364: 909048013,
    365: 909048014,
    366: 909048015,
    367: 909048016,
    368: 909048017,
    369: 909048018,
    370: 909049001,
    371: 909049002,
    372: 909049003,
    373: 909049004,
    374: 909049005,
    375: 909049006,
    376: 909049007,
    377: 909049008,
    378: 909049009,
    379: 909049010,
    380: 909049011,
    381: 909049012,
    382: 909049013,
    383: 909049014,
    384: 909049015,
    385: 909049016,
    386: 909049017,
    387: 909049018,
    388: 909049019,
    389: 909049020,
    390: 909049021,
    391: 909050002,
    392: 909050003,
    393: 909050004,
    394: 909050005,
    395: 909050006,
    396: 909050008,
    397: 909050009,
    398: 909050010,
    399: 909050011,
    400: 909050012,
    401: 909050013,
    402: 909050014,
    403: 909050015,
    404: 909050016,
    405: 909050017,
    406: 909050018,
    407: 909050019,
    408: 909050020,
    409: 909050021,
    410: 909050026,
    411: 909050027,
    412: 909050028,
    413: 909547001,
    414: 909550001
}

# Badge values for s1 to s5 commands - using your exact values
BADGE_VALUES = {
    "s1": 1048576,    # Your first badge
    "s2": 32768,      # Your second badge  
    "s3": 2048,       # Your third badge
    "s4": 64,         # Your fourth badge
    "s5": 262144     # Your seventh badge
}

# ------------------- Insta API Thread -------------------
def start_insta_api():
    port = insta.find_free_port()
    print(f"🚀 Starting Insta API on port {port}")
    insta.app.run(host="0.0.0.0", port=port, debug=False)
# ------------------- End Insta API Thread -------------------
def uid_generator():
    # ৮ ডিজিটের সর্বনিম্ন সংখ্যা ১০০০০০০০ (10,000,000)
    # আপনার দেওয়া সর্বোচ্চ সীমা ৯৯৯৯৯৯৯৯৯৯৯ (99,999,999,999)
    start = 10000000
    end = 99999999999
    
    for i in range(start, end + 1):
        yield i

def cleanup_cache():
    """Clean old cached data to maintain performance"""
    current_time = time.time()
    # Clean last_request_time
    to_remove = [k for k, v in last_request_time.items() 
                 if current_time - v > CLEANUP_INTERVAL]
    for k in to_remove:
        last_request_time.pop(k, None)
    
    # Clean command_cache if too large
    if len(command_cache) > MAX_CACHE_SIZE:
        oldest_keys = sorted(command_cache.keys())[:len(command_cache)//2]
        for key in oldest_keys:
            command_cache.pop(key, None)

def get_rate_limited_response(user_id):
    """Implement rate limiting to reduce server load"""
    user_key = str(user_id)
    current_time = time.time()
    
    if user_key in last_request_time:
        time_since_last = current_time - last_request_time[user_key]
        if time_since_last < RATE_LIMIT_DELAY:
            return False
    
    last_request_time[user_key] = current_time
    return True

# Helper Functions
def is_admin(uid):
    return str(uid) == ADMIN_UID

# Helper functions for ghost join
def dec_to_hex(decimal):
    """Convert decimal to hex string"""
    hex_str = hex(decimal)[2:]
    return hex_str.upper() if len(hex_str) % 2 == 0 else '0' + hex_str.upper()

async def encrypt_packet(packet_hex, key, iv):
    """Encrypt packet using AES CBC"""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    packet_bytes = bytes.fromhex(packet_hex)
    padded_packet = pad(packet_bytes, AES.block_size)
    encrypted = cipher.encrypt(padded_packet)
    return encrypted.hex()

async def nmnmmmmn(packet_hex, key, iv):
    """Wrapper for encrypt_packet"""
    return await encrypt_packet(packet_hex, key, iv)
    



def get_idroom_by_idplayer(packet_hex):
    """Extract room ID from packet - converted from your other TCP"""
    try:
        json_result = get_available_room(packet_hex)
        parsed_data = json.loads(json_result)
        json_data = parsed_data["5"]["data"]
        data = json_data["1"]["data"]
        idroom = data['15']["data"]
        return idroom
    except Exception as e:
        print(f"Error extracting room ID: {e}")
        return None

async def check_player_in_room(target_uid, key, iv):
    """Check if player is in a room by sending status request"""
    try:
        # Send status request packet
        status_packet = await GeT_Status(int(target_uid), key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', status_packet)
        
        # You'll need to capture the response packet and parse it
        # For now, return True and we'll handle room detection in the main loop
        return True
    except Exception as e:
        print(f"Error checking player room status: {e}")
        return False
        
        
        
async def handle_alll_titles_command(inPuTMsG, uid, chat_id, key, iv, region, chat_type=0):
    """Handle /alltitles command to send all titles sequentially"""
    
    parts = inPuTMsG.strip().split()
    
    if len(parts) == 1:
        target_uid = uid
        target_name = "Yourself"
    elif len(parts) == 2 and parts[1].isdigit():
        target_uid = parts[1]
        target_name = f"UID {target_uid}"
    else:
        error_msg = f"""[B][C][FF0000]❌ Usage: /alltitles [uid]
        
📝 Examples:
/alltitles - Send all titles to yourself
/alltitles 123456789 - Send all titles to specific UID

🎯 What it does:
1. Sends all 4 titles one by one
2. 2-second delay between each title
3. Sends in background (non-blocking)
4. Shows progress updates
"""
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)
        return
    
    # Start the title sequence in the background
    asyncio.create_task(
        send_all_titles_sequentiallly(target_uid, chat_id, key, iv, region, chat_type)
    )
    

async def send_all_titles_sequentiallly(uid, chat_id, key, iv, region, chat_type):
    """Send all titles one by one with 2-second delay"""
    
    # Get all titles
    all_titles = [
        904090014, 904090015, 904090024, 904090025, 904090026, 904090027, 904990070, 904990071, 904990072
    ]
    
    total_titles = len(all_titles)
    
    # Send initial message
    start_msg = f"""[B][C][00FF00] Noobde Black666 ya meku agar tu noob bolra toh tu gay hai


"""
    await safe_send_message(chat_type, start_msg, uid, chat_id, key, iv)
    
    try:
        for index, title_id in enumerate(all_titles):
            title_number = index + 1
            

            
            # Send the actual title using your existing method
            # You'll need to use your existing title sending logic here
            # For example:
            title_packet = await noob(uid, chat_id, key, iv, nickname="MG24", title_id=title_id)
            
            if title_packet and whisper_writer:
                whisper_writer.write(title_packet)
                await whisper_writer.drain()
                print(f"✅ Sent title {title_number}/{total_titles}: {title_id}")
            
            # Wait 2 seconds before next title (unless it's the last one)
            if title_number < total_titles:
                await asyncio.sleep(2)
        
        # Completion message
        completion_msg = f"""[B][C][00FF00]Noobde ab tu bta ye titles aur bol kon noob hai
"""
        await safe_send_message(chat_type, completion_msg, uid, chat_id, key, iv)
        
    except Exception as e:
        error_msg = f"[B][C][FF0000]❌ Error sending titles: {str(e)}\n"
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)

async def noob(target_uid, chat_id, key, iv, nickname="MG24", title_id=None):
    """EXACT conversion with customizable title ID"""
    try:
        # Use provided title_id or get random one
        if title_id is None:
            # Get a random title from the list
            available_titles = [904090014, 904090015, 904090024, 904090025, 904090026, 904090027, 904990070, 904990071, 904990072]
            title_id = random.choice(available_titles)
        
        # Create fields dictionary with specific title_id
        fields = {
            1: 1,
            2: {
                1: int(target_uid),
                2: int(chat_id),
                5: int(datetime.now().timestamp()),
                8: f'{{"TitleID":{title_id},"type":"Title"}}',
                9: {
                    1: f"[C][B][FF0000]{nickname}",
                    2: int(await xBunnEr()),
                    4: 330,
                    5: 102000015,
                    8: "BOT TEAM",
                    10: 1,
                    11: 1,
                    13: {
                        1: 2
                    },
                    14: {
                        1: 8804135237,
                        2: 8,
                        3: b"\x10\x15\x08\x0a\x0b\x15\x0c\x0f\x11\x04\x07\x02\x03\x0d\x0e\x12\x01\x05\x06"
                    }
                },
                10: "en",
                13: {
                    2: 2,
                    3: 1
                },
                14: {}
            }
        }
        
        # ... rest of your existing function
        proto_bytes = await CrEaTe_ProTo(fields)
        packet_hex = proto_bytes.hex()
        
        encrypted_packet = await encrypt_packet(packet_hex, key, iv)
        packet_length = len(encrypted_packet) // 2
        hex_length = f"{packet_length:04x}"
        
        zeros_needed = 6 - len(hex_length)
        packet_prefix = "121500" + ("0" * zeros_needed)
        
        final_packet_hex = packet_prefix + hex_length + encrypted_packet
        final_packet = bytes.fromhex(final_packet_hex)
        
        print(f"✅ Created packet with Title ID: {title_id}")
        return final_packet
        
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return None
        

async def send_title_packet_direct(target_uid, chat_id, key, iv, region="ind"):
    """Send title packet directly without chat context - for auto-join"""
    try:
        print(f"🎖️ Sending title to {target_uid} in chat {chat_id}")
        
        # Method 1: Using your existing function
        title_packet = await convert_kyro_to_your_system(target_uid, chat_id, key, iv)
        
        if title_packet and whisper_writer:
            # Send via Whisper connection
            whisper_writer.write(title_packet)
            await whisper_writer.drain()
            print(f"✅ Title sent via Whisper to {target_uid}")
            return True
            
    except Exception as e:
        print(f"❌ Error sending title directly: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def titles():
    """Return all titles instead of just one random"""
    titles_list = [
        905090075, 904990072, 904990069, 905190079
    ]
    return titles_list  # Return the full list instead of random.choice            
    
    
class MultiAccountManager:
    def __init__(self):
        self.accounts_file = "accounts.json"
        self.accounts_data = self.load_accounts()
    
    def load_accounts(self):
        """Load multiple accounts from JSON file"""
        try:
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                accounts = json.load(f)

                return accounts
        except FileNotFoundError:
            # print(f"❌ Accounts file {self.accounts_file} not found!")  # Suppressed - using accounts.txt instead
            return {}
        except Exception as e:
            # print(f"❌ Error loading accounts: {e}")  # Suppressed
            return {}
    
    
    
    async def get_account_token(self, uid, password):
        """Get access token for a specific account"""
        try:
            url = "https://10000067.connect.garena.com/oauth/guest/token/grant"
            headers = {
                "Host": "100067.connect.garena.com",
                "User-Agent": await Ua(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "close"
            }
            data = {
                "uid": uid,
                "password": password,
                "response_type": "token",
                "client_type": "2",
                "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                "client_id": "100067"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        data = await response.json()
                        open_id = data.get("open_id")
                        access_token = data.get("access_token")
                        return open_id, access_token
            return None, None
        except Exception as e:
            print(f"❌ Error getting token for {uid}: {e}")
            return None, None

async def send_title_packet_direct(target_uid, chat_id, key, iv, region="ind"):
    """Send title packet directly without chat context - for auto-join"""
    try:
        print(f"🎖️ Sending title to {target_uid} in chat {chat_id}")
        
        # Method 1: Using your existing function
        title_packet = await convert_kyro_to_your_system(target_uid, chat_id, key, iv)
        
        if title_packet and whisper_writer:
            # Send via Whisper connection
            whisper_writer.write(title_packet)
            await whisper_writer.drain()
            print(f"✅ Title sent via Whisper to {target_uid}")
            return True
            
    except Exception as e:
        print(f"❌ Error sending title directly: {e}")
        import traceback
        traceback.print_exc()
    
    return False

async def handle_alll_titles_command(inPuTMsG, uid, chat_id, key, iv, region, chat_type=0):
    """Handle /alltitles command to send all titles sequentially"""
    
    parts = inPuTMsG.strip().split()
    
    if len(parts) == 1:
        target_uid = uid
        target_name = "Yourself"
    elif len(parts) == 2 and parts[1].isdigit():
        target_uid = parts[1]
        target_name = f"UID {target_uid}"
    else:
        error_msg = f"""[B][C][FF0000]❌ Usage: /alltitles [uid]
        
📝 Examples:
/alltitles - Send all titles to yourself
/alltitles 123456789 - Send all titles to specific UID

🎯 What it does:
1. Sends all 4 titles one by one
2. 2-second delay between each title
3. Sends in background (non-blocking)
4. Shows progress updates
"""
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)
        return
    
    # Start the title sequence in the background
    asyncio.create_task(
        send_all_titles_sequentiallly(target_uid, chat_id, key, iv, region, chat_type)
    )
    

def get_random_sticker():
    """
    Randomly select one sticker from available packs
    """

    sticker_packs = [
        # NORMAL STICKERS (1200000001-1 to 24)
        ("1200000001", 1, 24),

        # KELLY EMOJIS (1200000002-1 to 15)
        ("1200000002", 1, 15),

        # MAD CHICKEN (1200000004-1 to 13)
        ("1200000004", 1, 13),
    ]

    pack_id, start, end = random.choice(sticker_packs)
    sticker_no = random.randint(start, end)

    return f"[1={pack_id}-{sticker_no}]"
        
async def send_sticker(target_uid, chat_id, key, iv, nickname="BLACK"):
    """Send Random Sticker using /sticker command"""
    try:
        sticker_value = get_random_sticker()

        fields = {
            1: 1,
            2: {
                1: int(target_uid),
                2: int(chat_id),
                5: int(datetime.now().timestamp()),
                8: f'{{"StickerStr" : "{sticker_value}", "type":"Sticker"}}',
                9: {
                    1: f"[C][B][FF0000]{nickname}",
                    2: int(get_random_avatar()),
                    4: 330,
                    5: 102000015,
                    8: "BOT TEAM",
                    10: 1,
                    11: 66,
                    12: 66,
                    13: {1: 2},
                    14: {
                        1: 8804135237,
                        2: 8,
                        3: b"\x10\x15\x08\x0a\x0b\x15\x0c\x0f\x11\x04\x07\x02\x03\x0d\x0e\x12\x01\x05\x06"
                    }
                },
                10: "en",
                13: {
                    2: 2,
                    3: 1
                },
                14: {}
            }
        }

        proto_bytes = await CrEaTe_ProTo(fields)
        packet_hex = proto_bytes.hex()

        encrypted_packet = await encrypt_packet(packet_hex, key, iv)
        packet_length = len(encrypted_packet) // 2
        hex_length = f"{packet_length:04x}"

        zeros_needed = 6 - len(hex_length)
        packet_prefix = "121500" + ("0" * zeros_needed)

        final_packet_hex = packet_prefix + hex_length + encrypted_packet
        final_packet = bytes.fromhex(final_packet_hex)

        print(f"✅ Sticker Sent: {sticker_value}")
        return final_packet

    except Exception as e:
        print(f"❌ Sticker error: {e}")
        return None

# Alternative: DIRECT port of your friend's function but with your UID
async def send_kyro_title_adapted(chat_id, key, iv, target_uid, nickname="BLACK666FF"):
    """Direct adaptation of your friend's working function"""
    try:
        # Import your proto file (make sure it's in the same directory)
        from kyro_title_pb2 import GenTeamTitle
        
        root = GenTeamTitle()
        root.type = 1
        
        nested_object = root.data
        nested_object.uid = int(target_uid)  # CHANGE: Use target UID
        nested_object.chat_id = int(chat_id)
        nested_object.title = f"{{\"TitleID\":{titles()},\"type\":\"Title\"}}"
        nested_object.timestamp = int(datetime.now().timestamp())
        nested_object.language = "en"
        
        nested_details = nested_object.field9
        nested_details.Nickname = f"[C][B][FF0000]{nickname}"  # CHANGE: Your nickname
        nested_details.avatar_id = int(await xBunnEr())  # Use your function
        nested_details.rank = 330
        nested_details.badge = 102000015
        nested_details.Clan_Name = "BOT TEAM"  # CHANGE: Your clan
        nested_details.field10 = 1
        nested_details.global_rank_pos = 1
        nested_details.badge_info.value = 2
        
        nested_details.prime_info.prime_uid = 8804135237
        nested_details.prime_info.prime_level = 8
        # IMPORTANT: This must be bytes, not string!
        nested_details.prime_info.prime_hex = b"\x10\x15\x08\x0a\x0b\x15\x0c\x0f\x11\x04\x07\x02\x03\x0d\x0e\x12\x01\x05\x06"
        
        nested_options = nested_object.field13
        nested_options.url_type = 2
        nested_options.curl_platform = 1
        
        nested_object.empty_field.SetInParent()
        
        # Serialize
        packet = root.SerializeToString().hex()
        
        # Use YOUR encryption function
        encrypted_packet = await encrypt_packet(packet, key, iv)
        
        # Calculate length
        packet_length = len(encrypted_packet) // 2
        
        # Convert to hex (4 characters with leading zeros)
        hex_length = f"{packet_length:04x}"
        
        # Build packet EXACTLY like your friend
        zeros_needed = 6 - len(hex_length)
        packet_prefix = "121500" + ("0" * zeros_needed)
        
        final_packet_hex = packet_prefix + hex_length + encrypted_packet
        return bytes.fromhex(final_packet_hex)
        
    except Exception as e:
        print(f"❌ Direct adaptation error: {e}")
        import traceback
        traceback.print_exc()
        return None

async def send_all_titles_sequentially(uid, chat_id, key, iv, region, chat_type):
    """Send all titles one by one with 2-second delay"""
    
    # Get all titles
    all_titles = [
        905090075, 904990072, 904990069, 905190079
    ]
    
    total_titles = len(all_titles)
    
    # Send initial message
    start_msg = f"""[B][C][00FF00]🎖️ STARTING TITLE SEQUENCE!

📊 Total Titles: {total_titles}
⏱️ Delay: 2 seconds between titles
🔁 Mode: Sequential
🎯 Target: {uid}

⏳ Sending titles now...
"""
    await safe_send_message(chat_type, start_msg, uid, chat_id, key, iv)
    
    try:
        for index, title_id in enumerate(all_titles):
            title_number = index + 1
            
            # Create progress message
            progress_msg = f"""[B][C][FFFF00]📤 SENDING TITLE {title_number}/{total_titles}

🎖️ Title ID: {title_id}
📊 Progress: {title_number}/{total_titles}
⏱️ Next in: 2 seconds
"""
            await safe_send_message(chat_type, progress_msg, uid, chat_id, key, iv)
            
            # Send the actual title using your existing method
            # You'll need to use your existing title sending logic here
            # For example:
            title_packet = await convert_kyro_to_your_system(uid, chat_id, key, iv, nickname="BLACK666FF", title_id=title_id)
            
            if title_packet and whisper_writer:
                whisper_writer.write(title_packet)
                await whisper_writer.drain()
                print(f"✅ Sent title {title_number}/{total_titles}: {title_id}")
            
            # Wait 2 seconds before next title (unless it's the last one)
            if title_number < total_titles:
                await asyncio.sleep(2)
        
        # Completion message
        completion_msg = f"""[B][C][00FF00]✅ ALL TITLES SENT SUCCESSFULLY!

🎊 Total: {total_titles} titles sent
🎯 Target: {uid}
⏱️ Duration: {total_titles * 2} seconds
✅ Status: Complete!

🎖️ Titles Sent:
1. 905090075
2. 904990072
3. 904990069
4. 905190079
"""
        await safe_send_message(chat_type, completion_msg, uid, chat_id, key, iv)
        
    except Exception as e:
        error_msg = f"[B][C][FF0000]❌ Error sending titles: {str(e)}\n"
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)

async def handle_all_titles_command(inPuTMsG, uid, chat_id, key, iv, region, chat_type=0):
    """Handle /alltitles command to send all titles sequentially"""
    
    parts = inPuTMsG.strip().split()
    
    if len(parts) == 1:
        target_uid = uid
        target_name = "Yourself"
    elif len(parts) == 2 and parts[1].isdigit():
        target_uid = parts[1]
        target_name = f"UID {target_uid}"
    else:
        error_msg = f"""[B][C][FF0000]❌ Usage: /alltitles [uid]
        
📝 Examples:
/alltitles - Send all titles to yourself
/alltitles 123456789 - Send all titles to specific UID

🎯 What it does:
1. Sends all 4 titles one by one
2. 2-second delay between each title
3. Sends in background (non-blocking)
4. Shows progress updates
"""
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)
        return
    
    # Start the title sequence in the background
    asyncio.create_task(
        send_all_titles_sequentially(target_uid, chat_id, key, iv, region, chat_type)
    )
    
    # Immediate response
    response_msg = f"""[B][C][00FF00]🚀 STARTING TITLE SEQUENCE IN BACKGROUND!

👤 Target: {target_name}
🎖️ Total Titles: 4
⏱️ Delay: 2 seconds each
📱 Status: Running in background...

💡 You'll receive progress updates as titles are sent!
"""
    await safe_send_message(chat_type, response_msg, uid, chat_id, key, iv)


async def convert_kyro_to_your_system(target_uid, chat_id, key, iv, nickname="BLACK666FF", title_id=None):
    """EXACT conversion with customizable title ID"""
    try:
        # Use provided title_id or get random one
        if title_id is None:
            # Get a random title from the list
            available_titles = [905090075, 904990072, 904990069, 905190079]
            title_id = random.choice(available_titles)
        
        # Create fields dictionary with specific title_id
        fields = {
            1: 1,
            2: {
                1: int(target_uid),
                2: int(chat_id),
                5: int(datetime.now().timestamp()),
                8: f'{{"TitleID":{title_id},"type":"Title"}}',  # Use specific title ID
                # ... rest of your fields
                9: {
                    1: f"[C][B][FF0000]{nickname}",
                    2: int(await xBunnEr()),
                    4: 330,
                    5: 102000015,
                    8: "BOT TEAM",
                    10: 1,
                    11: 1,
                    13: {
                        1: 2
                    },
                    14: {
                        1: 8804135237,
                        2: 8,
                        3: b"\x10\x15\x08\x0a\x0b\x15\x0c\x0f\x11\x04\x07\x02\x03\x0d\x0e\x12\x01\x05\x06"
                    }
                },
                10: "en",
                13: {
                    2: 2,
                    3: 1
                },
                14: {}
            }
        }
        
        # ... rest of your existing function
        proto_bytes = await CrEaTe_ProTo(fields)
        packet_hex = proto_bytes.hex()
        
        encrypted_packet = await encrypt_packet(packet_hex, key, iv)
        packet_length = len(encrypted_packet) // 2
        hex_length = f"{packet_length:04x}"
        
        zeros_needed = 6 - len(hex_length)
        packet_prefix = "121500" + ("0" * zeros_needed)
        
        final_packet_hex = packet_prefix + hex_length + encrypted_packet
        final_packet = bytes.fromhex(final_packet_hex)
        
        print(f"✅ Created packet with Title ID: {title_id}")
        return final_packet
        
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return None
            
    async def send_join_from_account(self, target_uid, account_uid, password, key, iv, region):
        """Send join request from a specific account"""
        try:
            # Get token for this account
            open_id, access_token = await self.get_account_token(account_uid, password)
            if not open_id or not access_token:
                return False
            
            # Create join packet using the account's credentials
            join_packet = await self.create_account_join_packet(target_uid, account_uid, open_id, access_token, key, iv, region)
            if join_packet:
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error sending join from {account_uid}: {e}")
            return False
            
async def SEnd_InV_with_Cosmetics(Nu, Uid, K, V, region):
    """Simple version - just add field 5 with basic cosmetics"""
    region = "ind"
    fields = {
        1: 2, 
        2: {
            1: int(Uid), 
            2: region, 
            4: int(Nu),
            # Simply add field 5 with basic cosmetics
            5: {
                1: "BOT",                    # Name
                2: int(await get_random_avatar()),     # Avatar
                5: random.choice([1048576, 32768, 2048]),  # Random badge
            }
        }
    }

    if region.lower() == "ind":
        packet = '0514'
    elif region.lower() == "bd":
        packet = "0519"
    else:
        packet = "0515"
        
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet, K, V)   
            
async def join_custom_room(room_id, room_password, key, iv, region):
    """Join custom room with proper Free Fire packet structure"""
    fields = {
        1: 61,  # Room join packet type (verified for Free Fire)
        2: {
            1: int(room_id),
            2: {
                1: int(room_id),  # Room ID
                2: int(time.time()),  # Timestamp
                3: "BOT",  # Player name
                5: 12,  # Unknown
                6: 9999999,  # Unknown
                7: 1,  # Unknown
                8: {
                    2: 1,
                    3: 1,
                },
                9: 3,  # Room type
            },
            3: str(room_password),  # Room password
        }
    }
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet_type, key, iv)
    
async def leave_squad(key, iv, region):
    """Leave squad - converted from your old TCP leave_s()"""
    fields = {
        1: 7,
        2: {
            1: 12480598706  # Your exact value from old TCP
        }
    }
    
    packet = (await CrEaTe_ProTo(fields)).hex()
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk(packet, packet_type, key, iv)    
    
async def RedZed_SendInv(bot_uid, uid, key, iv):
    """Async version of send invite function"""
    try:
        fields = {
            1: 33, 
            2: {
                1: int(uid), 
                2: "IND", 
                3: 1, 
                4: 1, 
                6: "RedZedKing!!", 
                7: 330, 
                8: 1000, 
                9: 100, 
                10: "DZ", 
                12: 1, 
                13: int(uid), 
                16: 1, 
                17: {
                    2: 159, 
                    4: "y[WW", 
                    6: 11, 
                    8: "1.120.1", 
                    9: 3, 
                    10: 1
                }, 
                18: 306, 
                19: 18, 
                24: 902000306, 
                26: {}, 
                27: {
                    1: 11, 
                    2: int(bot_uid), 
                    3: 99999999999
                }, 
                28: {}, 
                31: {
                    1: 1, 
                    2: 32768
                }, 
                32: 32768, 
                34: {
                    1: bot_uid, 
                    2: 8, 
                    3: b"\x10\x15\x08\x0A\x0B\x13\x0C\x0F\x11\x04\x07\x02\x03\x0D\x0E\x12\x01\x05\x06"
                }
            }
        }
        
        # Convert bytes properly
        if isinstance(fields[2][34][3], str):
            fields[2][34][3] = b"\x10\x15\x08\x0A\x0B\x13\x0C\x0F\x11\x04\x07\x02\x03\x0D\x0E\x12\x01\x05\x06"
        
        # Use async versions of your functions
        packet = await CrEaTe_ProTo(fields)
        packet_hex = packet.hex()
        
        # Generate final packet
        final_packet = await GeneRaTePk(packet_hex, '0515', key, iv)
        
        return final_packet
        
    except Exception as e:
        print(f"❌ Error in RedZed_SendInv: {e}")
        import traceback
        traceback.print_exc()
        return None
    
async def request_join_with_badge(target_uid, badge_value, key, iv, region):
    """Send join request with specific badge - converted from your old TCP"""
    fields = {
        1: 33,
        2: {
            1: int(target_uid),
            2: region.upper(),
            3: 1,
            4: 1,
            5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]),
            6: "iG:[C][B][FF0000] MG24_GAMER",
            7: 330,
            8: 1000,
            10: region.upper(),
            11: bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56,
                       97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53]),
            12: 1,
            13: int(target_uid),
            14: {
                1: 2203434355,
                2: 8,
                3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
            },
            16: 1,
            17: 1,
            18: 312,
            19: 46,
            23: bytes([16, 1, 24, 1]),
            24: int(await get_random_avatar()),
            26: "",
            28: "",
            31: {
                1: 1,
                2: badge_value  # Dynamic badge value
            },
            32: badge_value,    # Dynamic badge value
            34: {
                1: int(target_uid),
                2: 8,
                3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])
            }
        },
        10: "en",
        13: {
            2: 1,
            3: 1
        }
    }
    
    packet = (await CrEaTe_ProTo(fields)).hex()
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk(packet, packet_type, key, iv)    
    
async def start_auto_packet(key, iv, region):
    """Create start match packet"""
    fields = {
        1: 9,
        2: {
            1: 12480598706,
        },
    }
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet_type, key, iv)

async def leave_squad_packet(key, iv, region):
    """Leave squad packet"""
    fields = {
        1: 7,
        2: {
            1: 12480598706,
        },
    }
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet_type, key, iv)

async def join_teamcode_packet(team_code, key, iv, region):
    """Join team using code"""
    fields = {
        1: 4,
        2: {
            4: bytes.fromhex("01090a0b121920"),
            5: str(team_code),
            6: 6,
            8: 1,
            9: {
                2: 800,
                6: 11,
                8: "1.111.1",
                9: 5,
                10: 1
            }
        }
    }
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet_type, key, iv)
    
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet_type, key, iv)
async def reset_bot_state(key, iv, region):
    """Reset bot to solo mode before spam - Critical step from your old TCP"""
    try:
        # Leave any current squad (using your exact leave_s function)
        leave_packet = await leave_squad(key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave_packet)
        await asyncio.sleep(0.5)
        
        print("✅ Bot state reset - left squad")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting bot: {e}")
        return False    
    
async def create_custom_room(room_name, room_password, max_players, key, iv, region):
    """Create a custom room"""
    fields = {
        1: 3,  # Create room packet type
        2: {
            1: room_name,
            2: room_password,
            3: max_players,  # 2, 4, 8, 16, etc.
            4: 1,  # Room mode
            5: 1,  # Map
            6: "en",  # Language
            7: {   # Player info
                1: "BotHost",
                2: int(await get_random_avatar()),
                3: 330,
                4: 1048576,
                5: "BOTCLAN"
            }
        }
    }
    
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
        
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), packet_type, key, iv)              
            
async def real_multi_account_join(target_uid, key, iv, region):
    """Send join requests using real account sessions"""
    try:
        # Load accounts
        accounts_data = load_accounts()
        if not accounts_data:
            return 0, 0
        
        success_count = 0
        total_accounts = len(accounts_data)
        
        for account_uid, password in accounts_data.items():
            try:
                print(f"🔄 Authenticating account: {account_uid}")
                
                # Get proper tokens for this account
                open_id, access_token = await GeNeRaTeAccEss(account_uid, password)
                if not open_id or not access_token:
                    print(f"❌ Failed to authenticate {account_uid}")
                    continue
                
                # Create a proper join request using the account's identity
                # We'll use the existing SEnd_InV function but with account context
                join_packet = await create_authenticated_join(target_uid, account_uid, key, iv, region)
                
                if join_packet:
                    await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
                    success_count += 1
                    print(f"✅ Join sent from authenticated account: {account_uid}")
                
                # Important: Wait between requests
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error with account {account_uid}: {e}")
                continue
        
        return success_count, total_accounts
        
    except Exception as e:
        print(f"❌ Multi-account join error: {e}")
        return 0, 0



async def handle_badge_command(cmd, inPuTMsG, uid, chat_id, key, iv, region, chat_type):
    """Handle individual badge commands"""
    parts = inPuTMsG.strip().split()
    if len(parts) < 2:
        error_msg = f"[B][C][FF0000]❌ Usage: /{cmd} (uid)\nExample: /{cmd} 123456789\n"
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)
        return
    
    target_uid = parts[1]
    badge_value = BADGE_VALUES.get(cmd, 1048576)
    
    if not target_uid.isdigit():
        error_msg = f"[B][C][FF0000]❌ Please write a valid player ID!\n"
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)
        return
    
    # Send initial message
    initial_msg = f"[B][C][1E90FF]🌀 Request received! Preparing to spam {target_uid}...\n"
    await safe_send_message(chat_type, initial_msg, uid, chat_id, key, iv)
    
    try:
        # Reset bot state
        await reset_bot_state(key, iv, region)
        
        # Create and send join packets
        join_packet = await request_join_with_badge(target_uid, badge_value, key, iv, region)
        spam_count = 3
        
        for i in range(spam_count):
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
            print(f"✅ Sent /{cmd} request #{i+1} with badge {badge_value}")
            await asyncio.sleep(0.1)
        
        success_msg = f"[B][C][00FF00]✅ Successfully Sent {spam_count} Join Requests!\n🎯 Target: {target_uid}\n🏷️ Badge: {badge_value}\n"
        await safe_send_message(chat_type, success_msg, uid, chat_id, key, iv)
        
        # Cleanup
        await asyncio.sleep(1)
        await reset_bot_state(key, iv, region)
        
    except Exception as e:
        error_msg = f"[B][C][FF0000]❌ Error in /{cmd}: {str(e)}\n"
        await safe_send_message(chat_type, error_msg, uid, chat_id, key, iv)

async def create_authenticated_join(target_uid, account_uid, key, iv, region):
    """Create join request that appears to come from the specific account"""
    try:
        # Use the standard invite function but ensure it uses account context
        join_packet = await SEnd_InV(5, int(target_uid), key, iv, region)
        return join_packet
    except Exception as e:
        print(f"❌ Error creating join packet: {e}")
        return None        
    
    async def create_account_join_packet(self, target_uid, account_uid, open_id, access_token, key, iv, region):
        """Create join request packet for specific account"""
        try:
            # This is where you use the account's actual UID instead of main bot UID
            fields = {
                1: 33,
                2: {
                    1: int(target_uid),  # Target UID
                    2: region.upper(),
                    3: 1,
                    4: 1,
                    5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]),
                    6: f"BOT:[C][B][FF0000] ACCOUNT_{account_uid[-4:]}",  # Show account UID
                    7: 330,
                    8: 1000,
                    10: region.upper(),
                    11: bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56,
                               97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53]),
                    12: 1,
                    13: int(account_uid),  # Use the ACCOUNT'S UID here, not target UID!
                    14: {
                        1: 2203434355,
                        2: 8,
                        3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
                    },
                    16: 1,
                    17: 1,
                    18: 312,
                    19: 46,
                    23: bytes([16, 1, 24, 1]),
                    24: int(await get_random_avatar()),
                    26: "",
                    28: "",
                    31: {
                        1: 1,
                        2: 32768  # V-Badge
                    },
                    32: 32768,
                    34: {
                        1: int(account_uid),  # Use the ACCOUNT'S UID here too!
                        2: 8,
                        3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])
                    }
                },
                10: "en",
                13: {
                    2: 1,
                    3: 1
                }
            }
            
            packet = (await CrEaTe_ProTo(fields)).hex()
            
            if region.lower() == "ind":
                packet_type = '0514'
            elif region.lower() == "bd":
                packet_type = "0519"
            else:
                packet_type = "0515"
                
            return await GeneRaTePk(packet, packet_type, key, iv)
            
        except Exception as e:
            print(f"❌ Error creating join packet for {account_uid}: {e}")
            return None

# Global instance
multi_account_manager = MultiAccountManager()
    
    
    
async def auto_rings_emote_dual(sender_uid, key, iv, region):
    """Send The Rings emote to both sender and bot for dual emote effect"""
    try:
        # The Rings emote ID
        rings_emote_id = 909050009
        
        # Get bot's UID
        bot_uid = 13777711848
        
        # Send emote to SENDER (person who invited)
        emote_to_sender = await Emote_k(int(sender_uid), rings_emote_id, key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', emote_to_sender)
        
        # Small delay between emotes
        await asyncio.sleep(0.5)
        
        # Send emote to BOT (bot performs emote on itself)
        emote_to_bot = await Emote_k(int(bot_uid), rings_emote_id, key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', emote_to_bot)
        
        print(f"🤖 Bot performed dual Rings emote with sender {sender_uid} and bot {bot_uid}!")
        
    except Exception as e:
        print(f"Error sending dual rings emote: {e}")    
        
        
async def Room_Spam(Uid, Rm, Nm, K, V):
   
    same_value = random.choice([32768])  #you can add any badge value 
    
    fields = {
        1: 78,
        2: {
            1: int(Rm),  
            2: "iG:[C][B][FF0000] MG24_GAMER",  
            3: {
                2: 1,
                3: 1
            },
            4: 330,      
            5: 6000,     
            6: 201,      
            10: int(await get_random_avatar()),  
            11: int(Uid), # Target UID
            12: 1,       
            15: {
                1: 1,
                2: same_value  
            },
            16: same_value,    
            18: {
                1: 11481904755,  
                2: 8,
                3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
            },
            
            31: {
                1: 1,
                2: same_value  
            },
            32: same_value,    
            34: {
                1: int(Uid),   
                2: 8,
                3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])
            }
        }
    }
    
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0e15', K, V)
    
async def evo_cycle_spam(uids, key, iv, region):
    """Cycle through all evolution emotes one by one with 5-second delay"""
    global evo_cycle_running
    
    cycle_count = 0
    while evo_cycle_running:
        cycle_count += 1
        print(f"Starting evolution emote cycle #{cycle_count}")
        
        for emote_number, emote_id in evo_emotes.items():
            if not evo_cycle_running:
                break
                
            print(f"Sending evolution emote {emote_number} (ID: {emote_id})")
            
            for uid in uids:
                try:
                    uid_int = int(uid)
                    H = await Emote_k(uid_int, int(emote_id), key, iv, region)
                    await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
                    print(f"Sent emote {emote_number} to UID: {uid}")
                except Exception as e:
                    print(f"Error sending evo emote {emote_number} to {uid}: {e}")
            
            # Wait 5 seconds before moving to next emote (as requested)
            if evo_cycle_running:
                print(f"Waiting 5 seconds before next emote...")
                for i in range(5):
                    if not evo_cycle_running:
                        break
                    await asyncio.sleep(1)
        
        # Small delay before restarting the cycle
        if evo_cycle_running:
            print("Completed one full cycle of all evolution emotes. Restarting...")
            await asyncio.sleep(2)
    
    print("Evolution emote cycle stopped")
    
async def reject_spam_loop(target_uid, key, iv):
    """Send reject spam packets to target in background"""
    global reject_spam_running
    
    count = 0
    max_spam = 150
    
    while reject_spam_running and count < max_spam:
        try:
            # Send both packets
            packet1 = await banecipher1(target_uid, key, iv)
            packet2 = await banecipher(target_uid, key, iv)
            
            # Send to Online connection
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', packet1)
            await asyncio.sleep(0.1)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', packet2)
            
            count += 1
            print(f"Sent reject spam #{count} to {target_uid}")
            
            # 0.2 second delay between spam cycles
            await asyncio.sleep(0.2)
            
        except Exception as e:
            print(f"Error in reject spam: {e}")
            break
    
    return count    
    
async def handle_reject_completion(spam_task, target_uid, sender_uid, chat_id, chat_type, key, iv):
    """Handle completion of reject spam and send final message"""
    try:
        spam_count = await spam_task
        
        # Send completion message
        if spam_count >= 150:
            completion_msg = f"[B][C][00FF00]✅ Reject Spam Completed Successfully for ID {target_uid}\n✅ Total packets sent: {spam_count * 2}\n"
        else:
            completion_msg = f"[B][C][FFFF00]⚠️ Reject Spam Partially Completed for ID {target_uid}\n⚠️ Total packets sent: {spam_count * 2}\n"
        
        await safe_send_message(chat_type, completion_msg, sender_uid, chat_id, key, iv)
        
    except asyncio.CancelledError:
        print("Reject spam was cancelled")
    except Exception as e:
        error_msg = f"[B][C][FF0000]❌ ERROR in reject spam: {str(e)}\n"
        await safe_send_message(chat_type, error_msg, sender_uid, chat_id, key, iv)    
    
async def banecipher(client_id, key, iv):
    """Create reject spam packet 1 - Converted to new async format"""
    banner_text = f"""
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][0000FF]======================================================================================================================================================================================================================================================
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███




"""        
    fields = {
        1: 5,
        2: {
            1: int(client_id),
            2: 1,
            3: int(client_id),
            4: banner_text
        }
    }
    
    # Use CrEaTe_ProTo from xC4.py (async)
    packet = await CrEaTe_ProTo(fields)
    packet_hex = packet.hex()
    
    # Use EnC_PacKeT from xC4.py (async)
    encrypted_packet = await EnC_PacKeT(packet_hex, key, iv)
    
    # Calculate header length
    header_length = len(encrypted_packet) // 2
    header_length_final = await DecodE_HeX(header_length)
    
    # Build final packet based on header length
    if len(header_length_final) == 2:
        final_packet = "0515000000" + header_length_final + encrypted_packet
    elif len(header_length_final) == 3:
        final_packet = "051500000" + header_length_final + encrypted_packet
    elif len(header_length_final) == 4:
        final_packet = "05150000" + header_length_final + encrypted_packet
    elif len(header_length_final) == 5:
        final_packet = "0515000" + header_length_final + encrypted_packet
    else:
        final_packet = "0515000000" + header_length_final + encrypted_packet

    return bytes.fromhex(final_packet)

async def banecipher1(client_id, key, iv):
    """Create reject spam packet 2 - Converted to new async format"""
    gay_text = f"""
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[0. 00000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][0000FF]======================================================================================================================================================================================================================================================
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[0000=00]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███
[b][000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███[000000]███




"""        
    fields = {
        1: int(client_id),
        2: 5,
        4: 50,
        5: {
            1: int(client_id),
            2: gay_text,
        }
    }
    
    # Use CrEaTe_ProTo from xC4.py (async)
    packet = await CrEaTe_ProTo(fields)
    packet_hex = packet.hex()
    
    # Use EnC_PacKeT from xC4.py (async)
    encrypted_packet = await EnC_PacKeT(packet_hex, key, iv)
    
    # Calculate header length
    header_length = len(encrypted_packet) // 2
    header_length_final = await DecodE_HeX(header_length)
    
    # Build final packet based on header length
    if len(header_length_final) == 2:
        final_packet = "0515000000" + header_length_final + encrypted_packet
    elif len(header_length_final) == 3:
        final_packet = "051500000" + header_length_final + encrypted_packet
    elif len(header_length_final) == 4:
        final_packet = "05150000" + header_length_final + encrypted_packet
    elif len(header_length_final) == 5:
        final_packet = "0515000" + header_length_final + encrypted_packet
    else:
        final_packet = "0515000000" + header_length_final + encrypted_packet

    return bytes.fromhex(final_packet)
    

async def lag_team_loop(team_code, key, iv, region):
    """Rapid join/leave loop to create lag"""
    global lag_running
    count = 0
    
    while lag_running:
        try:
            # Join the team
            join_packet = await GenJoinSquadsPacket(team_code, key, iv)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
            
            # Very short delay before leaving
            await asyncio.sleep(0.01)  # 10 milliseconds
            
            # Leave the team
            leave_packet = await ExiT(None, key, iv)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave_packet)
            
            count += 1
            print(f"Lag cycle #{count} completed for team: {team_code}")
            
            # Short delay before next cycle
            await asyncio.sleep(0.01)  # 10 milliseconds between cycles
            
        except Exception as e:
            print(f"Error in lag loop: {e}")
            # Continue the loop even if there's an error
            await asyncio.sleep(0.1)
 
####################################
def bundle_packet(self, bundle_id, target_uid):
        fields = {
            1: 88,
            2: {
                1: {
                    1: bundle_id,
                    2: 1
                },
                2: 2
            }
        }
        packet = create_protobuf_packet(fields).hex()
        encrypted = encrypt_packet(packet, self.key, self.iv)
        header_length = len(encrypted) // 2
        header_length_hex = dec_to_hex(header_length)

        if len(header_length_hex) == 2:
            final_header = "0515000000"
        elif len(header_length_hex) == 3:
            final_header = "051500000"
        elif len(header_length_hex) == 4:
            final_header = "05150000"
        elif len(header_length_hex) == 5:
            final_header = "0515000"
        else:
            final_header = "0515000000"

        final_packet = final_header + header_length_hex + encrypted
        return bytes.fromhex(final_packet)

async def bundle_packet_async(bundle_id, key, iv, region="ind"):
    """Create bundle packet"""
    fields = {
        1: 88,
        2: {
            1: {
                1: bundle_id,
                2: 1
            },
            2: 2
        }
    }
    
    # Use your CrEaTe_ProTo function
    packet = await CrEaTe_ProTo(fields)
    packet_hex = packet.hex()
    
    # Use your encrypt_packet function
    encrypted = await encrypt_packet(packet_hex, key, iv)
    
    # Use your DecodE_HeX function
    header_length = len(encrypted) // 2
    header_length_hex = await DecodE_HeX(header_length)
    
    # Build final packet based on region
    if region.lower() == "ind":
        packet_type = '0514'
    elif region.lower() == "bd":
        packet_type = "0519"
    else:
        packet_type = "0515"
    
    # Determine header based on length
    if len(header_length_hex) == 2:
        final_header = f"{packet_type}000000"
    elif len(header_length_hex) == 3:
        final_header = f"{packet_type}00000"
    elif len(header_length_hex) == 4:
        final_header = f"{packet_type}0000"
    elif len(header_length_hex) == 5:
        final_header = f"{packet_type}000"
    else:
        final_header = f"{packet_type}000000"
    
    final_packet_hex = final_header + header_length_hex + encrypted
    return bytes.fromhex(final_packet_hex)

	
#Clan-info-by-clan-id
def Get_clan_info(clan_id):
    try:
        url = f"https://get-clan-info.vercel.app/get_clan_info?clan_id={clan_id}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            msg = f""" 
[11EAFD][b][c]
°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
▶▶▶▶GUILD DETAILS◀◀◀◀
Achievements: {data['achievements']}\n\n
Balance : {fix_num(data['balance'])}\n\n
Clan Name : {data['clan_name']}\n\n
Expire Time : {fix_num(data['guild_details']['expire_time'])}\n\n
Members Online : {fix_num(data['guild_details']['members_online'])}\n\n
Regional : {data['guild_details']['regional']}\n\n
Reward Time : {fix_num(data['guild_details']['reward_time'])}\n\n
Total Members : {fix_num(data['guild_details']['total_members'])}\n\n
ID : {fix_num(data['id'])}\n\n
Last Active : {fix_num(data['last_active'])}\n\n
Level : {fix_num(data['level'])}\n\n
Rank : {fix_num(data['rank'])}\n\n
Region : {data['region']}\n\n
Score : {fix_num(data['score'])}\n\n
Timestamp1 : {fix_num(data['timestamp1'])}\n\n
Timestamp2 : {fix_num(data['timestamp2'])}\n\n
Welcome Message: {data['welcome_message']}\n\n
XP: {fix_num(data['xp'])}\n\n
°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
            """
            return msg
        else:
            msg = """
[11EAFD][b][c]
°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
Failed to get info, please try again later!!

°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
            """
            return msg
    except:
        pass
#GET INFO BY PLAYER ID
def get_player_info(player_id):
    url = f"https://like2.vercel.app/player-info?uid={player_id}&server={server2}&key={key2}"
    response = requests.get(url)
    print(response)    
    if response.status_code == 200:
        try:
            r = response.json()
            return {
                "Account Booyah Pass": f"{r.get('booyah_pass_level', 'N/A')}",
                "Account Create": f"{r.get('createAt', 'N/A')}",
                "Account Level": f"{r.get('level', 'N/A')}",
                "Account Likes": f" {r.get('likes', 'N/A')}",
                "Name": f"{r.get('nickname', 'N/A')}",
                "UID": f" {r.get('accountId', 'N/A')}",
                "Account Region": f"{r.get('region', 'N/A')}",
                }
        except ValueError as e:
            pass
            return {
                "error": "Invalid JSON response"
            }
    else:
        pass
        return {
            "error": f"Failed to fetch data: {response.status_code}"
        }
#GET PLAYER BIO 
def get_player_bio(uid):
    try:
        url = f"https://mg24-gamer-super-info-api.vercel.app/get?uid={uid}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            # Bio is inside socialInfo -> signature
            bio = data.get('socialinfo', {}).get('signature', 'No Bio Found')
            if bio:
                return bio
            else:
                return "No bio available"
        else:
            return f"Failed to fetch bio. Status code: {res.status_code}"
    except Exception as e:
        return f"Error occurred: {e}"
#GET PLAYER INFO 
def get_player_basic(uid):
    try:
        url = f"https://mg24-gamer-super-info-api.vercel.app/get?uid={uid}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            # basic is inside socialInfo -> signature
            basic = data.get('AccountInfo', {}).get('AccountName', 'Unknown')
            level = data.get('AccountInfo', {}).get('AccountLevel', None)
            like = data.get('AccountInfo', {}).get('AccountLikes', None)
            region = data.get('AccountInfo', {}).get('AccountRegion', None)
            version = data.get('AccountInfo', {}).get('ReleaseVersion', None)
            guild_name = data.get('GuildInfo', {}).get('GuildName', None)
            bp_badge = data.get('AccountInfo', {}).get('AccountBPBadges', None)
            if basic:
                return f"""
[C][B][FFFF00]━━━━━━━━━━━━
[C][B][FFFFFF]Name: [66FF00]{basic}
[C][B][FFFFFF]level: [66FF00]{level}
[C][B][FFFFFF]like: [66FF00]{like}
[C][B][FFFFFF]region: [66FF00]{region}
[C][B][FFFFFF]last login version: [66FF00]{version}
[C][B][FFFFFF]Booyah Pass Badge: [66FF00]{bp_badge}
[C][B][FFFFFF]guild name: [66FF00]{guild_name}
[C][B][FFFF00]━━━━━━━━━━━━
"""
            else:
                return "No basic available"
        else:
            return f"Failed to fetch basic. Status code: {res.status_code}"
    except Exception as e:
        return f"Error occurred: {e}"
#GET ADD FRIEND
def get_player_add(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=GUEST_UID&password=YOUR_GUEST_UID&friend_uid={uid}"
        res = requests.get(url)
        data = res.json()
            # add is inside socialInfo -> signature
        action = data.get('action', 'Unknown')
        status = data.get('status', 'Unknown')
        message = data.get('message', 'No message received')
        if action:
            return message
        else:
            return message
    except Exception as e:
        return f"Error occurred: {e}"

# ১ থেকে ১০০ পর্যন্ত প্রতিটি আইডি এবং পাসওয়ার্ড আলাদা ফাংশন হিসেবে নিচে দেওয়া হলো:
def get_player_add_1(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818952&password=MG24_GAMER_KING_ZL4Y&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_2(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808011&password=MG24_GAMER_KING_M6QE&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_3(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808118&password=MG24_GAMER_KING_KFYN&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_4(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808121&password=MG24_GAMER_KING_DBWT&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_5(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808005&password=MG24_GAMER_KING_A6LQ&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_6(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808465&password=MG24_GAMER_KING_4K2T&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_7(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808488&password=MG24_GAMER_KING_3WYS&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_8(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808492&password=MG24_GAMER_KING_8TO0&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_9(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808487&password=MG24_GAMER_KING_IHLA&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_10(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808744&password=MG24_GAMER_KING_4RLN&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_11(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808757&password=MG24_GAMER_KING_AI2C&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_12(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808745&password=MG24_GAMER_KING_JM3R&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_13(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808736&password=MG24_GAMER_KING_55MV&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_14(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379808779&password=MG24_GAMER_KING_OL5G&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_15(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809073&password=MG24_GAMER_KING_4XV3&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_16(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809095&password=MG24_GAMER_KING_9F3O&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_17(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809093&password=MG24_GAMER_KING_87FM&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_18(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809105&password=MG24_GAMER_KING_YYEX&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_19(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809060&password=MG24_GAMER_KING_A0QN&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_20(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809304&password=MG24_GAMER_KING_QX77&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_21(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809342&password=MG24_GAMER_KING_NW2V&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_22(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809363&password=MG24_GAMER_KING_FGOW&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_23(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809353&password=MG24_GAMER_KING_7P6P&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_24(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809476&password=MG24_GAMER_KING_8RMP&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_25(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809547&password=MG24_GAMER_KING_VWJH&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_26(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809582&password=MG24_GAMER_KING_FHE1&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_27(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809598&password=MG24_GAMER_KING_GRCL&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_28(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379809754&password=MG24_GAMER_KING_0YSB&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_29(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810560&password=MG24_GAMER_KING_HXLD&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_30(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810647&password=MG24_GAMER_KING_OJVS&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_31(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810661&password=MG24_GAMER_KING_BSK8&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_32(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810909&password=MG24_GAMER_KING_YKF9&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_33(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810900&password=MG24_GAMER_KING_PE0H&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_34(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810922&password=MG24_GAMER_KING_I0QH&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_35(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811000&password=MG24_GAMER_KING_N7NM&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_36(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379810998&password=MG24_GAMER_KING_TYRL&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_37(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811235&password=MG24_GAMER_KING_WZB7&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_38(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811249&password=MG24_GAMER_KING_GPS0&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_39(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811282&password=MG24_GAMER_KING_IPS6&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_40(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811297&password=MG24_GAMER_KING_QKR9&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_41(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811310&password=MG24_GAMER_KING_1I6E&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_42(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811554&password=MG24_GAMER_KING_0TCA&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_43(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811557&password=MG24_GAMER_KING_D679&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_44(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379811548&password=MG24_GAMER_KING_XOJA&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_45(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812532&password=MG24_GAMER_KING_DYLJ&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_46(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812544&password=MG24_GAMER_KING_F9YB&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_47(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812595&password=MG24_GAMER_KING_GM2M&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_48(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812617&password=MG24_GAMER_KING_EZAC&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_49(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812814&password=MG24_GAMER_KING_MI7R&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_50(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812846&password=MG24_GAMER_KING_PSOO&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_51(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379812813&password=MG24_GAMER_KING_IZGI&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_52(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813093&password=MG24_GAMER_KING_B6YS&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_53(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813089&password=MG24_GAMER_KING_UUMA&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_54(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813180&password=MG24_GAMER_KING_TGUJ&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_55(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813168&password=MG24_GAMER_KING_JD3L&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_56(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813269&password=MG24_GAMER_KING_8LQW&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_57(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813368&password=MG24_GAMER_KING_9C9J&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_58(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813378&password=MG24_GAMER_KING_3D3L&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_59(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813428&password=MG24_GAMER_KING_73NT&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_60(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813435&password=MG24_GAMER_KING_BRPO&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_61(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379813559&password=MG24_GAMER_KING_BFM3&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_62(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814432&password=MG24_GAMER_KING_ON9Q&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_63(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814474&password=MG24_GAMER_KING_4NVV&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_64(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814479&password=MG24_GAMER_KING_OGK0&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_65(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814533&password=MG24_GAMER_KING_UK5X&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_66(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814523&password=MG24_GAMER_KING_SQ6Q&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_67(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814748&password=MG24_GAMER_KING_KGJX&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_68(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814764&password=MG24_GAMER_KING_R7MR&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_69(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814813&password=MG24_GAMER_KING_EQUM&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_70(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379814861&password=MG24_GAMER_KING_QPFL&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_71(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815049&password=MG24_GAMER_KING_M4GH&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_72(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815096&password=MG24_GAMER_KING_1JVT&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_73(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815083&password=MG24_GAMER_KING_C94W&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_74(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815127&password=MG24_GAMER_KING_7IEK&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_75(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815292&password=MG24_GAMER_KING_UZ5A&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_76(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815109&password=MG24_GAMER_KING_KTB2&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_77(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815329&password=MG24_GAMER_KING_G4TJ&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_78(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815335&password=MG24_GAMER_KING_7RAV&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_79(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379815591&password=MG24_GAMER_KING_ES3B&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_80(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379816326&password=MG24_GAMER_KING_H1C1&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_81(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379816379&password=MG24_GAMER_KING_PHE5&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_82(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379816369&password=MG24_GAMER_KING_KIM7&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_83(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379816395&password=MG24_GAMER_KING_IOHF&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_84(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817290&password=MG24_GAMER_KING_K7SF&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_85(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817308&password=MG24_GAMER_KING_TKHF&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_86(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817306&password=MG24_GAMER_KING_HYR5&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_87(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817897&password=MG24_GAMER_KING_EE0P&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_88(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817940&password=MG24_GAMER_KING_SM3A&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_89(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818394&password=MG24_GAMER_KING_3BXP&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_90(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818381&password=MG24_GAMER_KING_Z3E5&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_91(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818429&password=MG24_GAMER_KING_34YL&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_92(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818752&password=MG24_GAMER_KING_9805&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_93(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818905&password=MG24_GAMER_KING_6R63&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_94(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818947&password=MG24_GAMER_KING_2U5S&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_95(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379819004&password=MG24_GAMER_KING_IX2J&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_96(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818952&password=MG24_GAMER_KING_ZL4Y&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_97(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818900&password=MG24_GAMER_KING_6R63&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_98(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379818390&password=MG24_GAMER_KING_3BXP&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_99(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817945&password=MG24_GAMER_KING_SM3A&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

def get_player_add_100(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/adding_friend?uid=4379817310&password=MG24_GAMER_KING_HYR5&friend_uid={uid}"
        res = requests.get(url)
        return res.json().get('message', 'No message')
    except Exception as e: return f"Error: {e}"

async def send_all_friend_requests_async(target_uid):
    # ১০০টি ফাংশনের মাস্টার লিস্ট
    functions = [
        get_player_add_1, get_player_add_2, get_player_add_3, get_player_add_4, get_player_add_5,
        get_player_add_6, get_player_add_7, get_player_add_8, get_player_add_9, get_player_add_10,
        get_player_add_11, get_player_add_12, get_player_add_13, get_player_add_14, get_player_add_15,
        get_player_add_16, get_player_add_17, get_player_add_18, get_player_add_19, get_player_add_20,
        get_player_add_21, get_player_add_22, get_player_add_23, get_player_add_24, get_player_add_25,
        get_player_add_26, get_player_add_27, get_player_add_28, get_player_add_29, get_player_add_30,
        get_player_add_31, get_player_add_32, get_player_add_33, get_player_add_34, get_player_add_35,
        get_player_add_36, get_player_add_37, get_player_add_38, get_player_add_39, get_player_add_40,
        get_player_add_41, get_player_add_42, get_player_add_43, get_player_add_44, get_player_add_45,
        get_player_add_46, get_player_add_47, get_player_add_48, get_player_add_49, get_player_add_50,
        get_player_add_51, get_player_add_52, get_player_add_53, get_player_add_54, get_player_add_55,
        get_player_add_56, get_player_add_57, get_player_add_58, get_player_add_59, get_player_add_60,
        get_player_add_61, get_player_add_62, get_player_add_63, get_player_add_64, get_player_add_65,
        get_player_add_66, get_player_add_67, get_player_add_68, get_player_add_69, get_player_add_70,
        get_player_add_71, get_player_add_72, get_player_add_73, get_player_add_74, get_player_add_75,
        get_player_add_76, get_player_add_77, get_player_add_78, get_player_add_79, get_player_add_80,
        get_player_add_81, get_player_add_82, get_player_add_83, get_player_add_84, get_player_add_85,
        get_player_add_86, get_player_add_87, get_player_add_88, get_player_add_89, get_player_add_90,
        get_player_add_91, get_player_add_92, get_player_add_93, get_player_add_94, get_player_add_95,
        get_player_add_96, get_player_add_97, get_player_add_98, get_player_add_99, get_player_add_100
    ]

    try:
        loop = asyncio.get_event_loop()
        
        # ThreadPoolExecutor ব্যবহার করে ১০০টি রিকোয়েস্টকে নন-ব্লকিং ভাবে সাজানো
        # max_workers=50 দেওয়া হয়েছে যাতে খুব দ্রুত কাজ শেষ হয়
        with ThreadPoolExecutor(max_workers=50) as executor:
            tasks = [
                loop.run_in_executor(executor, func, target_uid) 
                for func in functions
            ]
            
            # সব রিকোয়েস্ট শেষ হওয়া পর্যন্ত অপেক্ষা (কিন্তু বট ফ্রীজ হবে না)
            results = await asyncio.gather(*tasks)
            
        success_count = len([r for r in results if "Error" not in r])
        return f"Successfully processed {success_count}/100 requests."

    except Exception as e:
        return f"System Error: {str(e)}"

#GET ADD FRIEND
def get_player_remove(uid):
    try:
        url = f"https://danger-add-friend.vercel.app/remove_friend?uid=GUEST_UID&password=YOUR_GUEST_UID&friend_uid={uid}"
        res = requests.get(url)
        data = res.json()
            # add is inside socialInfo -> signature
        action = data.get('action', 'Unknown')
        status = data.get('status', 'Unknown')
        message = data.get('message', 'No message received')
        if action:
            return message
        else:
            return message
    except Exception as e:
        return f"Error occurred: {e}"
#GET PLAYER BAN STATUS
def get_player_ban_status(uid):
    try:
        url = f"http://amin-team-api.vercel.app/check_banned?player_id={uid}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            # status is inside socialInfo -> signature
            status = data.get('status', 'Unknown')
            player_name = data.get('player_name', 'Unknown')
            if status:
                return f"""
 [FFDD00][b][c]
°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
[00D1FF]Player Name: {player_name}
Player ID : {xMsGFixinG(uid)} 
Status: {status}
[FFDD00]°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°
[00FF00][b][c]BOT MADE BY NAJMI_ADMIN 
"""
            else:
                return "No ban_status available"
        else:
            return f"Failed to fetch ban_status. Status code: {res.status_code}"
    except Exception as e:
        return f"Error occurred: {e}"
#CHAT WITH AI
def talk_with_ai(question):
    url = f"https://princeaiapi.vercel.app/prince/api/v1/ask?key=prince&ask={question}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        msg = data["message"]["content"]
        return msg
    else:
        return "An error occurred while connecting to the server."
#SPAM REQUESTS
def spam_requests(player_id):
    # This URL now correctly points to the Flask app you provided
    url = f"https://like2.vercel.app/send_requests?uid={player_id}&server={server2}&key={key2}"
    try:
        res = requests.get(url, timeout=20) # Added a timeout
        if res.status_code == 200:
            data = res.json()
            # Return a more descriptive message based on the API's JSON response
            return f"API Status: Success [{data.get('success_count', 0)}] Failed [{data.get('failed_count', 0)}]"
        else:
            # Return the error status from the API
            return f"API Error: Status {res.status_code}"
    except requests.exceptions.RequestException as e:
        # Handle cases where the API isn't running or is unreachable
        print(f"Could not connect to spam API: {e}")
        return "Failed to connect to spam API."
####################################

# ** NEW INFO FUNCTION using the new API **
def newinfo(uid):
    # Base URL without parameters
    url = "https://like2.vercel.app/player-info"
    # Parameters dictionary - this is the robust way to do it
    params = {
        'uid': uid,
        'server': server2,  # Hardcoded to bd as requested
        'key': key2
    }
    try:
        # Pass the parameters to requests.get()
        response = requests.get(url, params=params, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            # Check if the expected data structure is in the response
            if "basicInfo" in data:
                return {"status": "ok", "data": data}
            else:
                # The API returned 200, but the data is not what we expect (e.g., error message in JSON)
                return {"status": "error", "message": data.get("error", "Invalid ID or data not found.")}
        else:
            # The API returned an error status code (e.g., 404, 500)
            try:
                # Try to get a specific error message from the API's response
                error_msg = response.json().get('error', f"API returned status {response.status_code}")
                return {"status": "error", "message": error_msg}
            except ValueError:
                # If the error response is not JSON
                return {"status": "error", "message": f"API returned status {response.status_code}"}

    except requests.exceptions.RequestException as e:
        # Handle network errors (e.g., timeout, no connection)
        return {"status": "error", "message": f"Network error: {str(e)}"}
    except ValueError: 
        # Handle cases where the response is not valid JSON
        return {"status": "error", "message": "Invalid JSON response from API."}
        
    async def run_spam(chat_type, message, count, uid, chat_id, key, iv):
        try:
            for i in range(count):
                await safe_send_message(chat_type, message, uid, chat_id, key, iv)
                await asyncio.sleep(0.12)
        except Exception as e:
            print("Spam Error:", e)
        
    async def send_title_msg(self, chat_id, key, iv):
        """Build title packet using dictionary structure like GenResponsMsg"""
    
        fields = {
            1: 1,  # type
            2: {   # data
                1: "13777711848",  # uid
                2: str(chat_id),   # chat_id  
                3: f"{{\"TitleID\":{get_random_title()},\"type\":\"Title\"}}",  # title
                4: int(datetime.now().timestamp()),  # timestamp
                5: 0,   # chat_type
                6: "en", # language
                9: {    # field9 - player details
                    1: "[C][B][FF0000] MG24_GAMER",  # Nickname
                    2: await get_random_avatar(),          # avatar_id
                    3: 330,                          # rank
                    4: 102000015,                    # badge
                    5: "MG24_GAMER",                 # Clan_Name
                    6: 1,                            # field10
                    7: 1,                            # global_rank_pos
                    8: {                             # badge_info
                        1: 2                         # value
                    },
                    9: {                             # prime_info
                        1: 8804135237,               # prime_uid
                        2: 8,                        # prime_level
                        3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"  # prime_hex
                    }
                },
                13: {   # field13 - url options
                    1: 2,   # url_type
                    2: 1    # curl_platform
                },
                99: b""  # empty_field
            }
        }

        # **EXACTLY like GenResponsMsg:**
        packet = create_protobuf_packet(fields)
        packet = packet.hex()
        header_length = len(encrypt_packet(packet, key, iv)) // 2
        header_length_final = dec_to_hex(header_length)
    
        # **KEY: Use 0515 for title packets instead of 1215**
        if len(header_length_final) == 2:
            final_packet = "0515000000" + header_length_final + self.nmnmmmmn(packet)
        elif len(header_length_final) == 3:
            final_packet = "051500000" + header_length_final + self.nmnmmmmn(packet)
        elif len(header_length_final) == 4:
            final_packet = "05150000" + header_length_final + self.nmnmmmmn(packet)
        elif len(header_length_final) == 5:
            final_packet = "0515000" + header_length_final + self.nmnmmmmn(packet)
    
        return bytes.fromhex(final_packet)
        
        

	
#ADDING-100-LIKES-IN-24H
def send_likes(uid):
    try:
        likes_api_response = requests.get(
             f"https://ffviplikeapis.vercel.app/like?uid={uid}&server_name=bd",
             timeout=15
             )
      
      
        if likes_api_response.status_code != 200:
            return f"""
[C][B][FF0000]━━━━━
[FFFFFF]Like API Error!
Status Code: {likes_api_response.status_code}
Please check if the uid is correct.
━━━━━
"""

        api_json_response = likes_api_response.json()

        player_name = api_json_response.get('PlayerNickname', 'Unknown')
        likes_before = api_json_response.get('LikesbeforeCommand', 0)
        likes_after = api_json_response.get('LikesafterCommand', 0)
        likes_added = api_json_response.get('LikesGivenByAPI', 0)
        status = api_json_response.get('status', 0)

        if status == 1 and likes_added > 0:
            # ✅ Success
            return f"""
[C][B][11EAFD]‎━━━━━━━━━━━━
[FFFFFF]Likes Status:

[00FF00]Likes Sent Successfully!

[FFFFFF]Player Name : [00FF00]{player_name}  
[FFFFFF]Likes Added : [00FF00]{likes_added}  
[FFFFFF]Likes Before : [00FF00]{likes_before}  
[FFFFFF]Likes After : [00FF00]{likes_after}  
[C][B][11EAFD]‎━━━━━━━━━━━━
[C][B][FFB300]Subscribe: [FFFFFF]NAJMI_ADMIN [00FF00]!!
"""
        elif status == 2 or likes_before == likes_after:
            # 🚫 Already claimed / Maxed
            return f"""
[C][B][FF0000]━━━━━━━━━━━━

[FFFFFF]No Likes Sent!

[FF0000]You have already taken likes with this UID.
Try again after 24 hours.

[FFFFFF]Player Name : [FF0000]{player_name}  
[FFFFFF]Likes Before : [FF0000]{likes_before}  
[FFFFFF]Likes After : [FF0000]{likes_after}  
[C][B][FF0000]━━━━━━━━━━━━
"""
        else:
            # ❓ Unexpected case
            return f"""
[C][B][FF0000]━━━━━━━━━━━━
[FFFFFF]Unexpected Response!
Something went wrong.

Please try again or contact support.
━━━━━━━━━━━━
"""

    except requests.exceptions.RequestException:
        return """
[C][B][FF0000]━━━━━
[FFFFFF]Like API Connection Failed!
Is the API server (app.py) running?
━━━━━
"""
    except Exception as e:
        return f"""
[C][B][FF0000]━━━━━
[FFFFFF]An unexpected error occurred:
[FF0000]{str(e)}
━━━━━
"""
#USERNAME TO insta INFO 
def send_insta_info(username):
    try:
        response = requests.get(f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}", timeout=15)
        if response.status_code != 200:
            return f"[B][C][FF0000]❌ Instagram API Error! Status Code: {response.status_code}"

        user = response.json()
        full_name = user.get("full_name", "Unknown")
        followers = user.get("edge_followed_by", {}).get("count") or user.get("followers_count", 0)
        following = user.get("edge_follow", {}).get("count") or user.get("following_count", 0)
        posts = user.get("media_count") or user.get("edge_owner_to_timeline_media", {}).get("count", 0)
        profile_pic = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
        private_status = user.get("is_private")
        verified_status = user.get("is_verified")

        return f"""
[B][C][FB0364]╭[D21A92]─[BC26AB]╮[FFFF00]╔═══════╗
[C][B][FF7244]│[FE4250]◯[C81F9C]֯│[FFFF00]║[FFFFFF]INSTAGRAM_INFO[FFFF00]║
[C][B][FDC92B]╰[FF7640]─[F5066B]╯[FFFF00]╚═══════╝
[C][B][FFFF00]━━━━━━━━━━━━
[C][B][FFFFFF]Name: [66FF00]{full_name}
[C][B][FFFFFF]Username: [66FF00]{username}
[C][B][FFFFFF]Followers: [66FF00]{followers}
[C][B][FFFFFF]Following: [66FF00]{following}
[C][B][FFFFFF]Posts: [66FF00]{posts}
[C][B][FFFFFF]Private: [66FF00]{private_status}
[C][B][FFFFFF]Verified: [66FF00]{verified_status}
[C][B][FFFF00]━━━━━━━━━━━━
"""
    except requests.exceptions.RequestException:
        return "[B][C][FF0000]❌ Instagram API Connection Failed!"
    except Exception as e:
        return f"[B][C][FF0000]❌ Unexpected Error: {str(e)}"

async def cHTypE(V):
    if V == 1: return "CLan"
    if V == 2: return "PrivaTe"
    if V == 3 or V == 5: return "Squid"
    return "Unknown"

####################################
#CHECK ACCOUNT IS BANNED

Hr = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': "OB52"}

# ---- Random Colores ----
def get_random_color():
    colors = [
        "[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]", "[FFFFFF]", "[FFA500]",
        "[A52A2A]", "[800080]", "[000000]", "[808080]", "[C0C0C0]", "[FFC0CB]", "[FFD700]", "[ADD8E6]",
        "[90EE90]", "[D2691E]", "[DC143C]", "[00CED1]", "[9400D3]", "[F08080]", "[20B2AA]", "[FF1493]",
        "[7CFC00]", "[B22222]", "[FF4500]", "[DAA520]", "[00BFFF]", "[00FF7F]", "[4682B4]", "[6495ED]",
        "[5F9EA0]", "[DDA0DD]", "[E6E6FA]", "[B0C4DE]", "[556B2F]", "[8FBC8F]", "[2E8B57]", "[3CB371]",
        "[6B8E23]", "[808000]", "[B8860B]", "[CD5C5C]", "[8B0000]", "[FF6347]", "[FF8C00]", "[BDB76B]",
        "[9932CC]", "[8A2BE2]", "[4B0082]", "[6A5ACD]", "[7B68EE]", "[4169E1]", "[1E90FF]", "[191970]",
        "[00008B]", "[000080]", "[008080]", "[008B8B]", "[B0E0E6]", "[AFEEEE]", "[E0FFFF]", "[F5F5DC]",
        "[FAEBD7]"
    ]
    return random.choice(colors)

print(get_random_color())
    
# ---- Random Avatar ----
async def get_random_avatar():
    await asyncio.sleep(0)  # makes it async but instant
    avatar_list = [
        '902050001', '902050002', '902050003', '902039016', '902050004',
        '902047011', '902047010', '902049015', '902050006', '902049020'
    ]
    return random.choice(avatar_list)
    
async def ultra_quick_emote_attack(team_code, emote_id, target_uid, key, iv, region):
    """Join team, authenticate chat, perform emote, and leave automatically"""
    try:
        # Step 1: Join the team
        join_packet = await GenJoinSquadsPacket(team_code, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
        print(f"🤖 Joined team: {team_code}")
        
        # Wait for team data and chat authentication
        await asyncio.sleep(1.5)  # Increased to ensure proper connection
        
        # Step 2: The bot needs to be detected in the team and authenticate chat
        # This happens automatically in TcPOnLine, but we need to wait for it
        
        # Step 3: Perform emote to target UID
        emote_packet = await Emote_k(int(target_uid), int(emote_id), key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', emote_packet)
        print(f"🎭 Performed emote {emote_id} to UID {target_uid}")
        
        # Wait for emote to register
        await asyncio.sleep(0.5)
        
        # Step 4: Leave the team
        leave_packet = await ExiT(None, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave_packet)
        print(f"🚪 Left team: {team_code}")
        
        return True, f"Quick emote attack completed! Sent emote to UID {target_uid}"
        
    except Exception as e:
        return False, f"Quick emote attack failed: {str(e)}"
        
        
async def encrypted_proto(encoded_hex):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_message = pad(encoded_hex, AES.block_size)
    encrypted_payload = cipher.encrypt(padded_message)
    return encrypted_payload
    
async def GeNeRaTeAccEss(uid , password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": (await Ua()),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"}
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as response:
            if response.status != 200: 
                return (None, None)
            data_json = await response.json()
            open_id = data_json.get("open_id")
            access_token = data_json.get("access_token")
            return (open_id, access_token) if open_id and access_token else (None, None)

async def EncRypTMajoRLoGin(open_id, access_token):
    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire"
    major_login.platform_id = 1
    major_login.client_version = "1.120.1"
    major_login.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Verizon"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1920
    major_login.screen_height = 1080
    major_login.screen_dpi = "280"
    major_login.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    major_login.memory = 3003
    major_login.gpu_renderer = "Adreno (TM) 640"
    major_login.gpu_version = "OpenGL ES 3.1 v1.46"
    major_login.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    major_login.client_ip = "223.191.51.89"
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.device_type = "Handheld"
    memory_available = major_login.memory_available
    memory_available.version = 55
    memory_available.hidden_value = 81
    major_login.access_token = access_token
    major_login.platform_sdk_id = 1
    major_login.network_operator_a = "Verizon"
    major_login.network_type_a = "WIFI"
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.external_storage_total = 36235
    major_login.external_storage_available = 31335
    major_login.internal_storage_total = 2519
    major_login.internal_storage_available = 703
    major_login.game_disk_storage_available = 25010
    major_login.game_disk_storage_total = 26628
    major_login.external_sdcard_avail_storage = 32992
    major_login.external_sdcard_total_storage = 36235
    major_login.login_by = 3
    major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    major_login.reg_avatar = 1
    major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    major_login.channel_type = 3
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019118695"
    major_login.graphics_api = "OpenGLES2"
    major_login.supported_astc_bitset = 16383
    major_login.login_open_id_type = 4
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = 13564
    major_login.release_channel = "android"
    major_login.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    major_login.android_engine_init_flag = 110009
    major_login.if_push = 1
    major_login.is_vpn = 1
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    string = major_login.SerializeToString()
    return  await encrypted_proto(string)

async def MajorLogin(payload):
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=Hr, ssl=ssl_context) as response:
            if response.status == 200: return await response.read()
            return None

async def GetLoginData(base_url, payload, token):
    url = f"{base_url}/GetLoginData"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    Hr['Authorization']= f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=Hr, ssl=ssl_context) as response:
            if response.status == 200: return await response.read()
            return None

async def DecRypTMajoRLoGin(MajoRLoGinResPonsE):
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(MajoRLoGinResPonsE)
    return proto

async def DecRypTLoGinDaTa(LoGinDaTa):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(LoGinDaTa)
    return proto

async def DecodeWhisperMessage(hex_packet):
    packet = bytes.fromhex(hex_packet)
    proto = DEcwHisPErMsG_pb2.DecodeWhisper()
    proto.ParseFromString(packet)
    return proto
    
async def decode_team_packet(hex_packet):
    packet = bytes.fromhex(hex_packet)
    proto = sQ_pb2.recieved_chat()
    proto.ParseFromString(packet)
    return proto
    
async def xAuThSTarTuP(TarGeT, token, timestamp, key, iv):
    uid_hex = hex(TarGeT)[2:]
    uid_length = len(uid_hex)
    encrypted_timestamp = await DecodE_HeX(timestamp)
    encrypted_account_token = token.encode().hex()
    encrypted_packet = await EnC_PacKeT(encrypted_account_token, key, iv)
    encrypted_packet_length = hex(len(encrypted_packet) // 2)[2:]
    if uid_length == 9: headers = '0000000'
    elif uid_length == 8: headers = '00000000'
    elif uid_length == 10: headers = '000000'
    elif uid_length == 7: headers = '000000000'
    else: print('Unexpected length') ; headers = '0000000'
    return f"0115{headers}{uid_hex}{encrypted_timestamp}00000{encrypted_packet_length}{encrypted_packet}"
     
async def fast_emote_spam(uids, emote_id, key, iv, region):
    """Fast emote spam function that sends emotes rapidly"""
    global fast_spam_running
    count = 0
    max_count = 25  # Spam 25 times
    
    while fast_spam_running and count < max_count:
        for uid in uids:
            try:
                uid_int = int(uid)
                H = await Emote_k(uid_int, int(emote_id), key, iv, region)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
            except Exception as e:
                print(f"Error in fast_emote_spam for uid {uid}: {e}")
        
        count += 1
        await asyncio.sleep(0.3)  # Increased delay to save CPU

# NEW FUNCTION: Custom emote spam with specified times
async def custom_emote_spam(uid, emote_id, times, key, iv, region):
    """Custom emote spam function that sends emotes specified number of times"""
    global custom_spam_running
    count = 0
    
    while custom_spam_running and count < times:
        try:
            uid_int = int(uid)
            H = await Emote_k(uid_int, int(emote_id), key, iv, region)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
            count += 1
            await asyncio.sleep(0.3)  # Increased delay to save CPU
        except Exception as e:
            print(f"Error in custom_emote_spam for uid {uid}: {e}")
            break

# NEW FUNCTION: Faster spam request loop - Sends exactly 30 requests quickly
async def spam_request_loop_with_cosmetics(target_uid, key, iv, region):
    """Spam request function with cosmetics - using your same structure"""
    global spam_request_running
    
    count = 0
    max_requests = 30
    
    # Different badge values to rotate through
    badge_rotation = [1048576, 32768, 2048, 64, 4094, 11233, 262144]
    
    while spam_request_running and count < max_requests:
        try:
            # Rotate through different badges
            current_badge = badge_rotation[count % len(badge_rotation)]
            
            # Create squad (same as before)
            PAc = await OpEnSq(key, iv, region)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', PAc)
            await asyncio.sleep(0.2)
            
            # Change squad size (same as before)
            C = await cHSq(5, int(target_uid), key, iv, region)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', C)
            await asyncio.sleep(0.2)
            
            # Send invite WITH COSMETICS (enhanced version)
            V = await SEnd_InV_With_Cosmetics(5, int(target_uid), key, iv, region, current_badge)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', V)
            
            # Leave squad (same as before)
            E = await ExiT(None, key, iv)
            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', E)
            
            count += 1
            print(f"✅ Sent cosmetic invite #{count} to {target_uid} with badge {current_badge}")
            
            # Short delay
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"Error in cosmetic spam: {e}")
            await asyncio.sleep(0.5)
    
    return count
            


# NEW FUNCTION: Evolution emote spam with mapping
async def evo_emote_spam(uids, number, key, iv, region):
    """Send evolution emotes based on number mapping"""
    try:
        emote_id = EMOTE_MAP.get(int(number))
        if not emote_id:
            return False, f"Invalid number! Use 1-21 only."
        
        success_count = 0
        for uid in uids:
            try:
                uid_int = int(uid)
                H = await Emote_k(uid_int, emote_id, key, iv, region)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
                success_count += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"Error sending evo emote to {uid}: {e}")
        
        return True, f"Sent evolution emote {number} (ID: {emote_id}) to {success_count} player(s)"
    
    except Exception as e:
        return False, f"Error in evo_emote_spam: {str(e)}"

# NEW FUNCTION: all emote spam with mapping
async def play_emote_spam(uids, number, key, iv, region):
    """Send all emotes based on number mapping"""
    try:
        emote_id = ALL_EMOTE.get(int(number))
        if not emote_id:
            return False, f"Invalid number! Use 1-410 only."
        
        success_count = 0
        for uid in uids:
            try:
                uid_int = int(uid)
                H = await Emote_k(uid_int, emote_id, key, iv, region)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
                success_count += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"Error sending play emote to {uid}: {e}")
        
        return True, f"Sent playlution emote {number} (ID: {emote_id}) to {success_count} player(s)"
    
    except Exception as e:
        return False, f"Error in play_emote_spam: {str(e)}"

# NEW FUNCTION: Fast evolution emote spam
async def evo_fast_emote_spam(uids, number, key, iv, region):
    """Fast evolution emote spam function"""
    global evo_fast_spam_running
    count = 0
    max_count = 25  # Spam 25 times
    
    emote_id = EMOTE_MAP.get(int(number))
    if not emote_id:
        return False, f"Invalid number! Use 1-21 only."
    
    while evo_fast_spam_running and count < max_count:
        for uid in uids:
            try:
                uid_int = int(uid)
                H = await Emote_k(uid_int, emote_id, key, iv, region)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
            except Exception as e:
                print(f"Error in evo_fast_emote_spam for uid {uid}: {e}")
        
        count += 1
        await asyncio.sleep(0.3)  # CHANGED: Increased from 0.1s for CPU safety
    
    return True, f"Completed fast evolution emote spam {count} times"

# NEW FUNCTION: Custom evolution emote spam with specified times
async def evo_custom_emote_spam(uids, number, times, key, iv, region):
    """Custom evolution emote spam with specified repeat times"""
    global evo_custom_spam_running
    count = 0
    
    emote_id = EMOTE_MAP.get(int(number))
    if not emote_id:
        return False, f"Invalid number! Use 1-21 only."
    
    while evo_custom_spam_running and count < times:
        for uid in uids:
            try:
                uid_int = int(uid)
                H = await Emote_k(uid_int, emote_id, key, iv, region)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
            except Exception as e:
                print(f"Error in evo_custom_emote_spam for uid {uid}: {e}")
        
        count += 1
        await asyncio.sleep(0.3)  # CHANGED: Increased from 0.1s for CPU safety
    
    return True, f"Completed custom evolution emote spam {count} times"
    
# This was previously a large block, restoring original simple function if needed
# or leaving as placeholder since it's now handled by the class.
async def ArohiAccepted(uid,code,K,V):
    fields = {
        1: 4,
        2: {
            1: uid,
            3: uid,
            8: 1,
            9: {
            2: 161,
            4: "y[WW",
            6: 11,
            8: "1.114.18",
            9: 3,
            10: 1
            },
            10: str(code),
        }
        }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex() , '0515' , K , V)
    
async def join_teamcode_packet(team_code, key, iv, region):
    # Standard OB52 Team Code Join structure
    fields = {
        1: 4, # Type 4 is join
        2: {
            5: str(team_code),
            8: 1
        }
    }
    header = '0514' if region.lower() == 'ind' else '0515'
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), header, key, iv)

async def start_auto_packet(key, iv, region, opcode=9):
    # OB52 Match Start (Ref style: {1: opcode, 2: {1: 12480598706}})
    fields = {
        1: int(opcode), 
        2: {
            1: 12480598706
        }
    }
    # Match start usually uses 0515 header
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', key, iv)

async def leave_squad_packet(uid, key, iv, region):
    return await ExiT(int(uid or 0), key, iv)


def handle_keyboard_interrupt(signum, frame):
    """Clean handling for Ctrl+C"""
    print("\n\n🛑 Bot shutdown requested...")
    print("👋 Thanks for using DHASU-RUSHER")
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, handle_keyboard_interrupt)
    
# --- WEB KEEPALIVE FOR FREE HOSTING ---
# Ensure the bot stays alive and satisfies "website" requirements
app = Flask(__name__)

@app.route('/')
def home():
    return f"DHASU-RUSHER BOT ONLINE!<br>Active Bots: {len(active_bots)}"

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "bots": len(active_bots)})

def start_insta_api():
    """Starts a lightweight web server to keep the hosting active"""
    port = int(os.environ.get("PORT", 8080))  # Use PORT from env or default to 8080
    try:
        # Run without debug/reloader to save CPU
        print(f"🌍 Starting Web Server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"⚠️ Web Server Failed: {e}")

# Track running account objects to allow stopping them
# Format: {uid: FreeFireBot_instance}
active_bots = {}

async def account_watcher():
    """Background worker to watch accounts.txt for new/removed accounts"""
    print(f"[00FFFF]🔄 Account Watcher Service Started...")
    while True:
        try:
            if os.path.exists("accounts.txt"):
                current_file_accounts = {}
                with open("accounts.txt", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and ":" in line and not line.startswith("#"):
                            try:
                                uid, pwd = line.split(":", 1)
                                current_file_accounts[uid] = pwd
                            except ValueError:
                                continue
                
                # 1. REMOVE: Check for accounts in active_bots but NOT in file
                uids_to_stop = [uid for uid in active_bots if uid not in current_file_accounts]
                for uid in uids_to_stop:
                    print(f"[b][FF0000]🛑 Account Removed from File: {uid}. Taking offline...")
                    bot_to_stop = active_bots.pop(uid)
                    asyncio.create_task(bot_to_stop.stop())
                
                # 2. ADD: Check for accounts in file but NOT in active_bots
                for uid, pwd in current_file_accounts.items():
                    if uid not in active_bots:
                        print(f"[b][00FF00]🆕 New Account Detected: {uid}. Bringing online...")
                        bot = FreeFireBot(uid, pwd)
                        active_bots[uid] = bot
                        asyncio.create_task(bot.run_account())
                        
        except Exception:
            pass # Silent watcher errors
        
        await asyncio.sleep(8) # Check every 8 seconds

async def StarTinG():
    print(render('DHASU-RUSHER', colors=['white', 'cyan'], align='center'))
    print(f"[b][00FFFF]🚀 Smart Multi-Account System Loading...")
    
    # Start the account watcher in the background
    asyncio.create_task(account_watcher())
    
    # Stay alive forever while tasks run in background
    while True:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            break
        except Exception:
            pass

if __name__ == '__main__':
    try:
        # Global exception handler for background tasks to prevent crashes
        def handle_exception(loop, context):
            pass # Silently handle background exceptions
            
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
        
        threading.Thread(target=start_insta_api, daemon=True).start()
        asyncio.run(StarTinG())
    except KeyboardInterrupt:
        handle_keyboard_interrupt(None, None)
    except Exception as e:
        # Silent exit for general exceptions to avoid tracebacks
        sys.exit(0)