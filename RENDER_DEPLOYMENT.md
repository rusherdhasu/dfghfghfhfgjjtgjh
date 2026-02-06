# 🚀 Render.com Deployment Guide - DHASU-RUSHER Bot

## 📋 Prerequisites

1. ✅ GitHub account
2. ✅ Render.com account (free)
3. ✅ Discord bot token
4. ✅ Discord channel ID

---

## 🎯 Step-by-Step Deployment

### **Step 1: GitHub Setup (5 minutes)**

#### 1.1 Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `dhasu-rusher-bot` (ya koi bhi naam)
3. **IMPORTANT:** Select **"Private"** (sensitive data hai!)
4. Click **"Create repository"**

#### 1.2 Upload Code to GitHub

Open terminal in your bot folder:

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - DHASU-RUSHER Bot"

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/dhasu-rusher-bot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**⚠️ IMPORTANT:** `.gitignore` file already created hai, so `config.json` aur `accounts.txt` upload NAHI honge (security ke liye)!

---

### **Step 2: Render.com Setup (5 minutes)**

#### 2.1 Create Render Account

1. Go to https://render.com
2. Click **"Get Started for Free"**
3. Sign up with GitHub (recommended)

#### 2.2 Create New Web Service

1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Click **"Connect GitHub"** (if not connected)
4. Find your repository: `dhasu-rusher-bot`
5. Click **"Connect"**

#### 2.3 Configure Service

**Basic Settings:**
- **Name:** `dhasu-rusher-bot` (ya koi bhi naam)
- **Region:** Select closest to you (e.g., Singapore for India)
- **Branch:** `main`
- **Root Directory:** Leave blank
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python run_bot.py`

**Instance Type:**
- Select **"Free"** (₹0/month)

---

### **Step 3: Environment Variables (IMPORTANT!) 🔐**

Scroll down to **"Environment Variables"** section:

Click **"Add Environment Variable"** and add these:

#### Variable 1: DISCORD_BOT_TOKEN
```
Key: DISCORD_BOT_TOKEN
Value: YOUR_DISCORD_BOT_TOKEN_HERE
```

#### Variable 2: DISCORD_CHANNEL_ID
```
Key: DISCORD_CHANNEL_ID
Value: YOUR_CHANNEL_ID_HERE
```

#### Variable 3: ACCOUNTS (Multiple accounts in one variable)
```
Key: ACCOUNTS
Value: 4460548069:PASSWORD1,4460564221:PASSWORD2,4460580074:PASSWORD3
```

**Format:** `UID1:PASS1,UID2:PASS2,UID3:PASS3`

---

### **Step 4: Modify Code for Environment Variables**

Tumhe code mein chhota sa change karna padega to read environment variables:

#### Update `run_bot.py`:

Add this at the top (after imports):
```python
import os

# Load environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_CHANNEL = os.getenv('DISCORD_CHANNEL_ID')
ACCOUNTS_ENV = os.getenv('ACCOUNTS', '')
```

#### Update config loading:
```python
def load_config():
    # Try environment variables first
    if DISCORD_TOKEN and DISCORD_CHANNEL:
        return {
            'discord': {
                'bot_token': DISCORD_TOKEN,
                'command_channel_id': DISCORD_CHANNEL,
                'prefix': '/'
            },
            'settings': {
                'auto_reconnect': True,
                'log_discord_commands': True,
                'accounts_file': 'accounts.txt'
            }
        }
    
    # Fallback to config.json
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    return None
```

#### Update accounts loading:
```python
def load_accounts():
    # Try environment variable first
    if ACCOUNTS_ENV:
        accounts = {}
        for account_str in ACCOUNTS_ENV.split(','):
            if ':' in account_str:
                uid, password = account_str.split(':', 1)
                uid = uid.strip()
                accounts[uid] = {'uid': uid, 'password': password.strip()}
        return accounts
    
    # Fallback to accounts.txt
    accounts_file_path = os.path.join(os.path.dirname(__file__), 'accounts.txt')
    if os.path.exists(accounts_file_path):
        accounts = {}
        with open(accounts_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    uid, password = line.split(':', 1)
                    uid = uid.strip()
                    accounts[uid] = {'uid': uid, 'password': password.strip()}
        return accounts
    
    return {}
```

---

### **Step 5: Deploy! 🚀**

1. Click **"Create Web Service"** button at bottom
2. Wait for deployment (2-3 minutes)
3. Watch logs in real-time

**Expected logs:**
```
🤖 DHASU-RUSHER BOT LAUNCHER (Dynamic Reload)
📋 Configuration loaded successfully!
✅ Discord Bot logged in as Level-Bot
👁️ File watcher started
```

---

### **Step 6: Keep Bot Alive 24/7**

Render free tier **sleeps after 15 minutes of inactivity**. To keep it alive:

#### Option A: UptimeRobot (Recommended)

1. Go to https://uptimerobot.com
2. Sign up (free)
3. Add New Monitor:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** DHASU-RUSHER Bot
   - **URL:** Your Render URL (e.g., `https://dhasu-rusher-bot.onrender.com`)
   - **Monitoring Interval:** 5 minutes
4. Click **"Create Monitor"**

#### Option B: Cron-job.org

1. Go to https://cron-job.org
2. Sign up (free)
3. Create new cron job to ping your Render URL every 5 minutes

---

## ✅ Verification

### Check if Bot is Online:

1. **Render Dashboard:**
   - Go to your service
   - Check "Logs" tab
   - Should see: `✅ Discord Bot logged in`

2. **Discord:**
   - Bot should show as online
   - Try command: `/status`

3. **Test Dynamic Reload:**
   - Update environment variable `ACCOUNTS`
   - Click "Manual Deploy" → "Clear build cache & deploy"
   - New accounts should load

---

## 🔄 Updating Bot

### Method 1: Git Push (Recommended)

```bash
# Make changes to code
git add .
git commit -m "Updated bot"
git push

# Render will auto-deploy!
```

### Method 2: Manual Deploy

1. Go to Render dashboard
2. Click "Manual Deploy"
3. Select "Clear build cache & deploy"

---

## 📊 Monitoring

### View Logs:
1. Render Dashboard → Your Service → "Logs" tab
2. Real-time logs dikhenge

### Check Status:
- Discord command: `/status`
- Render dashboard: Service status

---

## ⚠️ Troubleshooting

### Bot Not Starting:
- Check environment variables
- Check logs for errors
- Verify `requirements.txt` has all dependencies

### Bot Sleeping:
- Set up UptimeRobot
- Verify ping is working

### Connection Errors:
- Check Garena server status
- Try different region on Render

---

## 🎯 Summary

**Total Time:** ~15 minutes
**Cost:** ₹0 (completely free!)
**Uptime:** 24/7 (with UptimeRobot)

**Files Created:**
- ✅ `requirements.txt` - Dependencies
- ✅ `.gitignore` - Protect sensitive files
- ✅ `Procfile` - Start command

**Next Steps:**
1. Push code to GitHub
2. Deploy on Render
3. Set environment variables
4. Set up UptimeRobot
5. Enjoy 24/7 bot! 🎉

---

**Made with ❤️ by DHASU-RUSHER**
