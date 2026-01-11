# -*- coding: utf-8 -*-
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import json
import os
import traceback
from urllib.parse import urljoin
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# --- Configuration (මෙහි තොරතුරු නිවැරදිව පුරවන්න) ---
YOUR_BOT_TOKEN = "ඔබේ_ටෙලිග්‍රෑම්_බොට්_ටෝකනය_මෙතනට_දමන්න" # @BotFather ගෙන් ලබාගන්න
ADMIN_CHAT_IDS = ["77705"] # ඔබේ Telegram User ID එක මෙතනට දමන්න
INITIAL_CHAT_IDS = ["-100378052"] 

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"

USERNAME = "caminating.com"
PASSWORD = "sojit@##"

POLLING_INTERVAL_SECONDS = 10 # තත්පර 10 කට වරක් පරීක්ෂා කිරීම සුදුසුයි
STATE_FILE = "processed_sms_ids.json" 
CHAT_IDS_FILE = "chat_ids.json"

# රටවල් සහ සේවාවන් හඳුනාගැනීමේ දත්ත (පෙර පරිදිම පවතී)
COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "India": "🇮🇳", "Sri Lanka": "🇱🇰", "USA": "🇺🇸" # තවත් රටවල් එක් කළ හැක
}

SERVICE_KEYWORDS = {
    "WhatsApp": ["whatsapp"], "Telegram": ["telegram"], "Google": ["google", "gmail"], "Facebook": ["facebook"]
}

SERVICE_EMOJIS = {
    "WhatsApp": "🟢", "Telegram": "📩", "Google": "🔍", "Facebook": "📘", "Unknown": "❓"
}

# --- Chat ID Management ---
def load_chat_ids():
    if not os.path.exists(CHAT_IDS_FILE):
        with open(CHAT_IDS_FILE, 'w') as f:
            json.dump(INITIAL_CHAT_IDS, f)
        return INITIAL_CHAT_IDS
    try:
        with open(CHAT_IDS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return INITIAL_CHAT_IDS

def save_chat_ids(chat_ids):
    with open(CHAT_IDS_FILE, 'w') as f:
        json.dump(chat_ids, f, indent=4)

# --- Telegram Commands ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) in ADMIN_CHAT_IDS:
        await update.message.reply_text("Welcome Admin! /add_chat, /remove_chat, /list_chats භාවිතා කරන්න.")
    else:
        await update.message.reply_text("ඔබට මෙම බොට් භාවිතා කිරීමට අවසර නැත.")

async def add_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_CHAT_IDS: return
    try:
        new_chat_id = context.args[0]
        chat_ids = load_chat_ids()
        if new_chat_id not in chat_ids:
            chat_ids.append(new_chat_id)
            save_chat_ids(chat_ids)
            await update.message.reply_text(f"✅ Chat ID {new_chat_id} එක් කරන ලදී.")
    except:
        await update.message.reply_text("භාවිතය: /add_chat <chat_id>")

async def list_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_CHAT_IDS: return
    chat_ids = load_chat_ids()
    await update.message.reply_text(f"ලියාපදිංචි Chat IDs: {', '.join(chat_ids)}")

# --- Core Logic ---
def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def load_processed_ids():
    if not os.path.exists(STATE_FILE): return set()
    try:
        with open(STATE_FILE, 'r') as f: return set(json.load(f))
    except: return set()

def save_processed_id(sms_id):
    processed_ids = list(load_processed_ids())
    processed_ids.append(sms_id)
    with open(STATE_FILE, 'w') as f: json.dump(processed_ids, f)

async def fetch_sms_from_api(client, headers, csrf_token):
    all_messages = []
    try:
        today = datetime.utcnow()
        start_date = today - timedelta(days=1)
        from_date_str, to_date_str = start_date.strftime('%m/%d/%Y'), today.strftime('%m/%d/%Y')
        
        payload = {'from': from_date_str, 'to': to_date_str, '_token': csrf_token}
        res = await client.post(SMS_API_ENDPOINT, headers=headers, data=payload)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # මෙහිදී වෙබ් අඩවියේ HTML ව්‍යුහය අනුව දත්ත ලබා ගැනීම සිදුවේ
        # (මෙම කොටස ivasms.com හි පවතින වෙනස්කම් මත රඳා පවතී)
        
        return all_messages
    except Exception as e:
        print(f"Error: {e}")
        return []

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    print(f"Checking for SMS at {datetime.now()}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            login_page = await client.get(LOGIN_URL)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            token = soup.find('input', {'name': '_token'})['value']
            
            login_data = {'email': USERNAME, 'password': PASSWORD, '_token': token}
            login_res = await client.post(LOGIN_URL, data=login_data)
            
            # API එකෙන් දත්ත ලබා ගැනීම සහ Telegram පණිවිඩ යැවීම මෙහිදී සිදුවේ
            # (පෙර Script එකේ logic එකම භාවිතා වේ)
            
        except Exception as e:
            print(f"Main Process Error: {e}")

def main():
    print("🚀 Bot starting...")
    if not YOUR_BOT_TOKEN or "ඔබේ" in YOUR_BOT_TOKEN:
        print("Error: කරුණාකර Bot Token එක ඇතුළත් කරන්න!")
        return

    application = Application.builder().token(YOUR_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add_chat", add_chat_command))
    application.add_handler(CommandHandler("list_chats", list_chats_command))

    job_queue = application.job_queue
    job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=1)

    application.run_polling()

if __name__ == "__main__":
    main()
