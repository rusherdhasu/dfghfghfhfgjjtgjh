# 🏥 UptimeRobot Setup Guide - Keep Bot Alive 24/7

## ⚠️ Problem

Render free tier **sleeps after 15 minutes** of inactivity:
- Bot goes offline
- Discord disconnects
- Free Fire bots stop

---

## ✅ Solution: UptimeRobot (100% FREE)

UptimeRobot will **ping your bot every 5 minutes** to keep it awake!

---

## 🚀 Setup Steps (5 minutes)

### Step 1: Deploy on Render First

Make sure your bot is deployed on Render and you have the URL:
```
https://your-bot-name.onrender.com
```

---

### Step 2: Create UptimeRobot Account

1. Go to https://uptimerobot.com
2. Click **"Sign Up Free"**
3. Enter email and create password
4. Verify email

---

### Step 3: Add Monitor

1. Click **"+ Add New Monitor"** button

2. Fill in details:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** `DHASU-RUSHER Bot`
   - **URL:** `https://your-bot-name.onrender.com/health`
   - **Monitoring Interval:** `5 minutes` (free tier)

3. Click **"Create Monitor"**

---

### Step 4: Verify

**Within 5 minutes:**
- UptimeRobot will show **"Up"** status (green)
- Your Render logs will show: `🏥 Health check server started`
- Bot will stay online 24/7!

---

## 📊 How It Works

```
Every 5 minutes:
  UptimeRobot → Ping /health endpoint
       ↓
  Render → Receives request
       ↓
  Bot → Stays awake!
```

---

## ✅ Verification

### Check UptimeRobot Dashboard:
- Status should be **"Up"** (green)
- Uptime should be **99%+**

### Check Render Logs:
```
🏥 Health check server started on port 8080
```

### Check Discord:
- Bot should show as **online**
- Commands should work: `/status`

---

## 🎯 Expected Results

**Before UptimeRobot:**
```
0-15 min: ✅ Bot online
15+ min: ❌ Bot sleeps
```

**After UptimeRobot:**
```
24/7: ✅ Bot online
```

---

## 🔧 Troubleshooting

### Monitor Shows "Down":
- Check Render URL is correct
- Make sure `/health` endpoint exists
- Check Render logs for errors

### Bot Still Sleeping:
- Verify monitoring interval is 5 minutes
- Check UptimeRobot is actually pinging
- Try manual ping: `curl https://your-bot.onrender.com/health`

---

## 💡 Alternative: Cron-job.org

If UptimeRobot doesn't work:

1. Go to https://cron-job.org
2. Sign up (free)
3. Create new cron job:
   - **Title:** DHASU-RUSHER Bot
   - **URL:** `https://your-bot.onrender.com/health`
   - **Schedule:** Every 5 minutes
4. Save

---

## 📋 Summary

**Total Time:** 5 minutes
**Cost:** ₹0 (completely free!)
**Result:** 24/7 uptime! 🎉

**Files Added:**
- ✅ `keep_alive.py` - Health check server
- ✅ Updated `run_bot.py` - Auto-start health server

**Next Steps:**
1. Deploy bot on Render
2. Get Render URL
3. Set up UptimeRobot monitor
4. Enjoy 24/7 bot! 🚀

---

**Made with ❤️ by DHASU-RUSHER**
