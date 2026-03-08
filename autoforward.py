import os
import asyncio
import threading
import pytz
import time
from datetime import datetime
from pyrogram import Client, errors
from telebot import TeleBot, types

# ==========================================
# SECTION 1: KOYEB CONFIGURATION
# ==========================================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION")
MY_ID = int(os.getenv("MY_ID", "0"))

# Target Groups: Format in Koyeb should be "@group1, @group2, @group3"
TARGET_GROUPS_RAW = os.getenv("TARGET_GROUPS", "")
TARGET_GROUPS = [g.strip() for g in TARGET_GROUPS_RAW.split(",") if g.strip()]

# ==========================================
# SECTION 2: INITIALIZATION
# ==========================================
AD_RUNNING = False
SAVED_MESSAGE = None  # Stores the forwarded ad data
PP_TIMEZONE = pytz.timezone("Asia/Phnom_Penh")

bot = TeleBot(BOT_TOKEN)
user_app = Client(
    "vinzy_user", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING_SESSION,
    in_memory=True
)

# ==========================================
# SECTION 3: USERBOT ADVERTISING LOGIC
# ==========================================

async def advertising_loop(from_chat_id, message_id):
    global AD_RUNNING
    async with user_app:
        while AD_RUNNING:
            now = datetime.now(PP_TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")
            print(f"[{now}] 📢 Starting Ad Round for {len(TARGET_GROUPS)} groups...")

            for group in TARGET_GROUPS:
                if not AD_RUNNING: break
                try:
                    # copy_message sends a clean post (no 'Forwarded' tag)
                    await user_app.copy_message(
                        chat_id=group, 
                        from_chat_id=from_chat_id, 
                        message_id=message_id
                    )
                    print(f"✅ Sent to {group}")
                    # 20-second delay between groups to avoid Telegram Spam Filters
                    await asyncio.sleep(20) 
                except Exception as e:
                    print(f"❌ Error for {group}: {e}")

            print(f"[{now}] ⏳ Round Complete. Waiting 1 hour...")
            # Breakable 1-hour sleep
            for _ in range(3600):
                if not AD_RUNNING: break
                await asyncio.sleep(1)

def start_ad_thread(c_id, m_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(advertising_loop(c_id, m_id))

# ==========================================
# SECTION 4: BOT CONTROL INTERFACE
# ==========================================

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📤 Set New Ad", "🚀 Start Processing")
    markup.row("🛑 Stop Ads", "📊 Status")
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    if message.from_user.id != MY_ID:
        bot.reply_to(message, "🚫 Unauthorized Access.")
        return
    bot.send_message(
        message.chat.id, 
        "🇰🇭 **Vinzy Ad Master (Phnom Penh)**\n\n1. Use 'Set New Ad'\n2. Forward your ad from your channel\n3. Click 'Start Processing'",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "📤 Set New Ad")
def ask_for_ad(message):
    if message.from_user.id != MY_ID: return
    msg = bot.send_message(message.chat.id, "📍 **Forward your Ad here now.**\n(Ensure it includes the images and emojis you want).")
    bot.register_next_step_handler(msg, save_forwarded_ad)

def save_forwarded_ad(message):
    global SAVED_MESSAGE
    SAVED_MESSAGE = {"chat_id": message.chat.id, "message_id": message.message_id}
    bot.reply_to(message, "✅ **Ad Loaded Successfully!** Ready to send.")

@bot.message_handler(func=lambda m: True)
def handle_control(message):
    global AD_RUNNING
    if message.from_user.id != MY_ID: return

    if message.text == "🚀 Start Processing":
        if not SAVED_MESSAGE:
            bot.reply_to(message, "❌ **Error:** No ad saved. Use 'Set New Ad' first.")
        elif not AD_RUNNING:
            AD_RUNNING = True
            threading.Thread(
                target=start_ad_thread, 
                args=(SAVED_MESSAGE['chat_id'], SAVED_MESSAGE['message_id']), 
                daemon=True
            ).start()
            bot.reply_to(message, "🚀 **Live!** Your account is now posting every 1 hour.")
        else:
            bot.reply_to(message, "⚠️ System is already active.")

    elif message.text == "🛑 Stop Ads":
        AD_RUNNING = False
        bot.reply_to(message, "🛑 **Stopped.** Processing will end after current group.")

    elif message.text == "📊 Status":
        status = "🟢 RUNNING" if AD_RUNNING else "🔴 IDLE"
        ad_check = "✅ READY" if SAVED_MESSAGE else "❌ EMPTY"
        now = datetime.now(PP_TIMEZONE).strftime("%H:%M")
        bot.reply_to(message, f"**Status:** {status}\n**Ad:** {ad_check}\n**Time:** {now} (PP)")

# ==========================================
# SECTION 5: SYSTEM STARTUP
# ==========================================
if __name__ == "__main__":
    print("🤖 Vinzy Bot is polling...")
    bot.infinity_polling(skip_pending=True)
