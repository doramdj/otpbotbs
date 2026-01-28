# -*- coding: utf-8 -*-
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
from urllib.parse import urljoin
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# --- Configuration ---
YOUR_BOT_TOKEN = "8254600761:AAE7m4xb9gt8f8ovasVOEo5nGn4CBL0wdqw"
ADMIN_CHAT_IDS = ["7459356628"] 
INITIAL_CHAT_IDS = ["-1003597884945"] 

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"

USERNAME = "ohlivvy53@gmail.com"
PASSWORD = "AAQidas123@"

POLLING_INTERVAL_SECONDS = 30 # Render වැනි platform සඳහා මෙය 30s වත් තැබීම සුදුසුයි
STATE_FILE = "processed_sms_ids.json" 
CHAT_IDS_FILE = "chat_ids.json"

# --- Country Flags & Service Keywords (පැරණි ලැයිස්තුවම භාවිතා කරන්න) ---
COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Argentina": "🇦🇷", "Australia": "🇦🇺", "Austria": "🇦🇹",
    "Bangladesh": "🇧🇩", "Belgium": "🇧🇪", "Brazil": "🇧🇷", "Canada": "🇨🇦", "China": "🇨🇳", "Egypt": "🇪🇬",
    "France": "🇫🇷", "Germany": "🇩🇪", "India": "🇮🇳", "Indonesia": "🇮🇩", "Italy": "🇮🇹", "Japan": "🇯🇵",
    "Malaysia": "🇲🇾", "Pakistan": "🇵🇰", "Russia": "🇷🇺", "Saudi Arabia": "🇸🇦", "Singapore": "🇸🇬",
    "South Africa": "🇿🇦", "Sri Lanka": "🇱🇰", "UAE": "🇦🇪", "UK": "🇬🇧", "USA": "🇺🇸", "Unknown": "🏴‍☠️"
}

SERVICE_KEYWORDS = {
    "Telegram": ["telegram"], "WhatsApp": ["whatsapp"], "Facebook": ["facebook", "meta"],
    "Google": ["google", "gmail", "g-"], "Instagram": ["instagram"], "TikTok": ["tiktok"],
    "Amazon": ["amazon"], "PayPal": ["paypal"], "Binance": ["binance"], "Netflix": ["netflix"]
}

SERVICE_EMOJIS = {
    "Telegram": "📩", "WhatsApp": "🟢", "Facebook": "📘", "Instagram": "📸",
    "Google": "🔍", "TikTok": "🎵", "Amazon": "🛒", "PayPal": "💰", "Unknown": "❓"
}

# --- Functions ---
def load_chat_ids():
    if not os.path.exists(CHAT_IDS_FILE):
        with open(CHAT_IDS_FILE, 'w') as f: json.dump(INITIAL_CHAT_IDS, f)
        return INITIAL_CHAT_IDS
    try:
        with open(CHAT_IDS_FILE, 'r') as f: return json.load(f)
    except: return INITIAL_CHAT_IDS

def save_chat_ids(chat_ids):
    with open(CHAT_IDS_FILE, 'w') as f: json.dump(chat_ids, f, indent=4)

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
    with open(STATE_FILE, 'w') as f: json.dump(processed_ids[-500:], f) # අන්තිම 500 පමණක් තබා ගනී

# --- Telegram Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_CHAT_IDS:
        await update.message.reply_text("✅ *Admin Authenticated*\n\nCommands:\n/add_chat <id>\n/list_chats", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Unauthorized access.")

async def add_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_CHAT_IDS: return
    try:
        new_id = context.args[0]
        cids = load_chat_ids()
        if new_id not in cids:
            cids.append(new_id)
            save_chat_ids(cids)
            await update.message.reply_text(f"✅ Added: `{new_id}`", parse_mode='MarkdownV2')
    except: await update.message.reply_text("Use: /add_chat <id>")

async def list_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_CHAT_IDS: return
    cids = load_chat_ids()
    msg = "📜 *Registered Chats:*\n" + "\n".join([f"- `{escape_markdown(c)}`" for c in cids])
    await update.message.reply_text(msg, parse_mode='MarkdownV2')

# --- SMS Fetching Logic ---
async def fetch_sms_from_api(client, headers, csrf_token):
    all_messages = []
    try:
        today = datetime.utcnow()
        start_date = today - timedelta(days=1)
        from_date_str, to_date_str = start_date.strftime('%m/%d/%Y'), today.strftime('%m/%d/%Y')
        
        payload = {'from': from_date_str, 'to': to_date_str, '_token': csrf_token}
        res = await client.post(SMS_API_ENDPOINT, headers=headers, data=payload)
        soup = BeautifulSoup(res.text, 'html.parser')
        group_divs = soup.find_all('div', {'class': 'pointer'})
        
        for div in group_divs:
            onclick = div.get('onclick', '')
            match = re.search(r"getDetials\('(.+?)'\)", onclick)
            if not match: continue
            group_id = match.group(1)
            
            num_url = urljoin(BASE_URL, "portal/sms/received/getsms/number")
            num_res = await client.post(num_url, headers=headers, data={'start': from_date_str, 'end': to_date_str, 'range': group_id, '_token': csrf_token})
            num_soup = BeautifulSoup(num_res.text, 'html.parser')
            num_divs = num_soup.select("div[onclick*='getDetialsNumber']")
            
            for ndiv in num_divs:
                phone_number = ndiv.text.strip()
                sms_url = urljoin(BASE_URL, "portal/sms/received/getsms/number/sms")
                sms_res = await client.post(sms_url, headers=headers, data={'start': from_date_str, 'end': to_date_str, 'Number': phone_number, 'Range': group_id, '_token': csrf_token})
                sms_soup = BeautifulSoup(sms_res.text, 'html.parser')
                cards = sms_soup.find_all('div', class_='card-body')
                
                for card in cards:
                    text_p = card.find('p', class_='mb-0')
                    if text_p:
                        sms_text = text_p.get_text(separator='\n').strip()
                        service = "Unknown"
                        for s_name, keywords in SERVICE_KEYWORDS.items():
                            if any(k in sms_text.lower() for k in keywords):
                                service = s_name; break
                        
                        code_match = re.search(r'\b(\d{4,8})\b', sms_text) or re.search(r'(\d{3}-\d{3})', sms_text)
                        code = code_match.group(1) if code_match else "N/A"
                        
                        all_messages.append({
                            "id": f"{phone_number}-{sms_text}",
                            "number": phone_number,
                            "country": group_id,
                            "flag": COUNTRY_FLAGS.get(group_id, "🏴‍☠️"),
                            "service": service,
                            "code": code,
                            "full_sms": sms_text
                        })
        return all_messages
    except Exception as e:
        print(f"API Error: {e}"); return []

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    headers = {'User-Agent': 'Mozilla/5.0'}
    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
        try:
            l_page = await client.get(LOGIN_URL)
            token = BeautifulSoup(l_page.text, 'html.parser').find('input', {'name': '_token'})['value']
            login_res = await client.post(LOGIN_URL, data={'email': USERNAME, 'password': PASSWORD, '_token': token})
            
            if "login" in str(login_res.url): return
            
            csrf = BeautifulSoup(login_res.text, 'html.parser').find('meta', {'name': 'csrf-token'})['content']
            messages = await fetch_sms_from_api(client, headers, csrf)
            
            p_ids = load_processed_ids()
            target_chats = load_chat_ids()
            
            for msg in reversed(messages):
                if msg["id"] not in p_ids:
                    s_emoji = SERVICE_EMOJIS.get(msg["service"], "❓")
                    full_msg = (f"🔔 *OTP Received*\n\n"
                               f"📞 *Number:* `{escape_markdown(msg['number'])}`\n"
                               f"🔑 *Code:* `{escape_markdown(msg['code'])}`\n"
                               f"🏆 *Service:* {s_emoji} {msg['service']}\n"
                               f"🌎 *Country:* {msg['flag']} {msg['country']}\n\n"
                               f"💬 *Message:*\n```\n{msg['full_sms']}\n```")
                    
                    for cid in target_chats:
                        try:
                            await context.bot.send_message(chat_id=cid, text=full_msg, parse_mode='MarkdownV2')
                        except: pass
                    save_processed_id(msg["id"])
        except Exception: print(traceback.format_exc())

# --- Startup Notification ---
async def post_init(application: Application):
    cids = load_chat_ids()
    for cid in cids:
        try:
            await application.bot.send_message(chat_id=cid, text="🚀 *Bot is Online and Monitoring SMS...*", parse_mode='MarkdownV2')
        except Exception as e:
            print(f"Startup notify failed for {cid}: {e}")

def main():
    # Build application with post_init hook
    app = Application.builder().token(YOUR_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("add_chat", add_chat_command))
    app.add_handler(CommandHandler("list_chats", list_chats_command))
    
    # SMS Job
    app.job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=5)
    
    print("🤖 Starting Bot...")
    app.run_polling(drop_pending_updates=True) # Conflict මඟහැරීමට පැරණි update මකා දමයි

if __name__ == "__main__":
    main()
