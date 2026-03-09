import os
import asyncio
import threading
import pytz
from datetime import datetime
from pyrogram import Client, errors
from telebot import TeleBot, types

# ==========================================
# SECTION 1: CONFIGURATION
# ==========================================
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
STRING_SESSION = os.getenv("STRING_SESSION", "").strip()

# Support for Multiple Admin IDs
MY_ID_RAW = os.getenv("MY_ID", "")
AUTHORIZED_USERS = [int(i.strip()) for i in MY_ID_RAW.split(",") if i.strip()]

TARGET_GROUPS_RAW = os.getenv("TARGET_GROUPS", "")
TARGET_GROUPS = [g.strip() for g in TARGET_GROUPS_RAW.split(",") if g.strip()]

# ==========================================
# SECTION 2: INITIALIZATION
# ==========================================
AD_RUNNING = False
SAVED_MESSAGE = None  
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
            print(f"[{now}] 📢 Starting Ad Round...")

            for group in TARGET_GROUPS:
                if not AD_RUNNING: break
                try:
                    # FIX 1: Resolve the peer first
                    chat_peer = await user_app.resolve_peer(group)
                    
                    # FIX 2: Copy the message using the resolved peer
                    await user_app.copy_message(
                        chat_id=group, 
                        from_chat_id=from_chat_id, 
                        message_id=message_id
                    )
                    print(f"✅ Sent to {group}")
                    await asyncio.sleep(20) # Spam protection
                except errors.FloodWait as e:
                    print(f"⚠️ Flood Wait: Sleeping {e.value}s")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(f"❌ Failed for {group}: {str(e)}")

            print(f"[{now}] ⏳ Round Complete. Waiting 1 hour...")
            for _ in range(3600):
                if not AD_RUNNING: break
                await asyncio.sleep(1)

def start_ad_thread(c_id, m_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(advertising_loop(c_id, m_id))

# ==========================================
# SECTION 4: BOT INTERFACE
# ==========================================

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📤 Set New Ad", "🚀 Start Processing")
    markup.row("🛑 Stop Ads", "📊 Status")
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    if message.from_user.id not in AUTHORIZED_USERS:
        return
    bot.send_message(
        message.chat.id, 
        "🇰🇭 **Vinzy Multi-Admin Active**\n1. Set Ad\n2. Start Processing",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "📤 Set New Ad")
def ask_for_ad(message):
    if message.from_user.id not in AUTHORIZED_USERS: return
    msg = bot.send_message(message.chat.id, "📍 **Forward the ad here now.**")
    bot.register_next_step_handler(msg, save_forwarded_ad)

def save_forwarded_ad(message):
    global SAVED_MESSAGE
    # We save the exact message details to ensure it isn't "empty"
    SAVED_MESSAGE = {"chat_id": message.chat.id, "message_id": message.message_id}
    bot.reply_to(message, "✅ **Ad Saved!** Both admins can now start the process.")

@bot.message_handler(func=lambda m: True)
def handle_control(message):
    global AD_RUNNING
    if message.from_user.id not in AUTHORIZED_USERS: return

    if message.text == "🚀 Start Processing":
        if not SAVED_MESSAGE:
            bot.reply_to(message, "❌ **Error:** No ad saved.")
        elif not AD_RUNNING:
            AD_RUNNING = True
            threading.Thread(
                target=start_ad_thread, 
                args=(SAVED_MESSAGE['chat_id'], SAVED_MESSAGE['message_id']), 
                daemon=True
            ).start()
            bot.reply_to(message, "🚀 **Live!** Posting to groups...")
        else:
            bot.reply_to(message, "⚠️ System is already active.")

    elif message.text == "🛑 Stop Ads":
        AD_RUNNING = False
        bot.reply_to(message, "🛑 **Stopped.**")

    elif message.text == "📊 Status":
        status = "🟢 RUNNING" if AD_RUNNING else "🔴 IDLE"
        bot.reply_to(message, f"**Status:** {status}\n**Groups:** {len(TARGET_GROUPS)}")

if __name__ == "__main__":
    print("🤖 Vinzy Bot is polling...")
    # skip_pending=True helps with the 409 Conflict error
    bot.infinity_polling(skip_pending=True)
