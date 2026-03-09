import os
import asyncio
import threading
import pytz
import re
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

MY_ID_RAW = os.getenv("MY_ID", "")
AUTHORIZED_USERS = [int(i.strip()) for i in MY_ID_RAW.split(",") if i.strip()]

# ==========================================
# SECTION 2: INITIALIZATION
# ==========================================
AD_RUNNING = False
TARGET_GROUPS = [] # Now starts empty; update via bot
USER_ADS = {}      # Stores {user_id: {"chat_id": x, "message_id": y}}
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

async def advertising_loop():
    global AD_RUNNING
    async with user_app:
        while AD_RUNNING:
            now = datetime.now(PP_TIMEZONE).strftime("%H:%M:%S")
            print(f"[{now}] 📢 Round started for {len(USER_ADS)} users...")

            for user_id, msg_data in list(USER_ADS.items()):
                if not AD_RUNNING: break
                
                for target in TARGET_GROUPS:
                    if not AD_RUNNING: break
                    try:
                        # Logic to handle IDs vs Links
                        if "t.me" in str(target):
                            try:
                                chat = await user_app.get_chat(target)
                                target_id = chat.id
                            except:
                                chat = await user_app.join_chat(target)
                                target_id = chat.id
                        else:
                            target_id = int(target)

                        await user_app.copy_message(
                            chat_id=target_id, 
                            from_chat_id=msg_data['chat_id'], 
                            message_id=msg_data['message_id']
                        )
                        print(f"  ✅ Sent for User {user_id} to {target}")
                        await asyncio.sleep(15) # Safety delay

                    except errors.FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        print(f"❌ Failed {target}: {str(e)}")

            print(f"⏳ Cycle complete. Next round in 1 hour.")
            for _ in range(3600):
                if not AD_RUNNING: break
                await asyncio.sleep(1)

def start_ad_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(advertising_loop())

# ==========================================
# SECTION 4: BOT INTERFACE
# ==========================================

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📤 Set My Ad", "🚀 Start System")
    markup.row("🛑 Stop All", "📊 Status")
    markup.row("🔗 Update Bulk Targets")
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    if message.from_user.id not in AUTHORIZED_USERS: return
    bot.send_message(
        message.chat.id, "🤖 **Vinzy Bot Multi-Ad Mode**\nPaste your targets and set your ads.",
        reply_markup=get_main_menu(), parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "📤 Set My Ad")
def ask_for_ad(message):
    if message.from_user.id not in AUTHORIZED_USERS: return
    msg = bot.send_message(message.chat.id, "📍 **Forward the ad you want me to post.**")
    bot.register_next_step_handler(msg, save_user_ad)

def save_user_ad(message):
    USER_ADS[message.from_user.id] = {"chat_id": message.chat.id, "message_id": message.message_id}
    bot.reply_to(message, "✅ **Your ad is saved!**")

@bot.message_handler(func=lambda m: m.text == "🔗 Update Bulk Targets")
def ask_for_targets(message):
    if message.from_user.id not in AUTHORIZED_USERS: return
    msg = bot.send_message(message.chat.id, "📝 **Send all links/IDs (comma or newline separated):**")
    bot.register_next_step_handler(msg, save_bulk_targets)

def save_bulk_targets(message):
    global TARGET_GROUPS
    TARGET_GROUPS = [i.strip() for i in re.split(r'[,\n]', message.text) if i.strip()]
    bot.reply_to(message, f"✅ **Target list updated!** Total: {len(TARGET_GROUPS)}")

@bot.message_handler(func=lambda m: True)
def handle_control(message):
    global AD_RUNNING
    if message.from_user.id not in AUTHORIZED_USERS: return

    if message.text == "🚀 Start System":
        if not TARGET_GROUPS:
            bot.reply_to(message, "❌ Use **Update Bulk Targets** first!")
        elif not USER_ADS:
            bot.reply_to(message, "❌ No ads saved. Use **Set My Ad**.")
        elif not AD_RUNNING:
            AD_RUNNING = True
            threading.Thread(target=start_ad_thread, daemon=True).start()
            bot.reply_to(message, "🚀 **System is now LIVE.**")
        else:
            bot.reply_to(message, "⚠️ Already running.")

    elif message.text == "🛑 Stop All":
        AD_RUNNING = False
        bot.reply_to(message, "🛑 **System stopped.**")

    elif message.text == "📊 Status":
        status = "🟢 RUNNING" if AD_RUNNING else "🔴 IDLE"
        bot.reply_to(message, f"**Status:** {status}\n**Active Ads:** {len(USER_ADS)}\n**Groups:** {len(TARGET_GROUPS)}")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
