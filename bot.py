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

# --- Configuration (මෙහි තොරතුරු නිවැරදිව ඇතුළත් කරන්න) ---
YOUR_BOT_TOKEN = "8254600761:AAE7m4xb9gt8f8ovasVOEo5nGn4CBL0wdqw" # <--- ඔබේ Token එක මෙතනට දමන්න
ADMIN_CHAT_IDS = ["7459356628"] 
INITIAL_CHAT_IDS = ["-1003597884945"] 

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"

USERNAME = "ohlivvy53@gmail.com"
PASSWORD = "AAQidas123@"

POLLING_INTERVAL_SECONDS = 2 
STATE_FILE = "processed_sms_ids.json" 
CHAT_IDS_FILE = "chat_ids.json"

# --- Country Flags & Service Keywords ---
COUNTRY_FLAGS = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "Andorra": "🇦🇩", "Angola": "🇦🇴",
    "Argentina": "🇦🇷", "Armenia": "🇦🇲", "Australia": "🇦🇺", "Austria": "🇦🇹", "Azerbaijan": "🇦🇿",
    "Bahrain": "🇧🇭", "Bangladesh": "🇧🇩", "Belarus": "🇧🇾", "Belgium": "🇧🇪", "Benin": "🇧🇯",
    "Bhutan": "🇧🇹", "Bolivia": "🇧🇴", "Brazil": "🇧🇷", "Bulgaria": "🇧🇬", "Burkina Faso": "🇧🇫",
    "Cambodia": "🇰🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Chad": "🇹🇩", "Chile": "🇨🇱",
    "China": "🇨🇳", "Colombia": "🇨🇴", "Congo": "🇨🇬", "Croatia": "🇭🇷", "Cuba": "🇨🇺",
    "Cyprus": "🇨🇾", "Czech Republic": "🇨🇿", "Denmark": "🇩🇰", "Egypt": "🇪🇬", "Estonia": "🇪🇪",
    "Ethiopia": "🇪🇹", "Finland": "🇫🇮", "France": "🇫🇷", "Gabon": "🇬🇦", "Gambia": "🇬🇲",
    "Georgia": "🇬🇪", "Germany": "🇩🇪", "Ghana": "🇬🇭", "Greece": "🇬🇷", "Guatemala": "🇬🇹",
    "Guinea": "🇬🇳", "Haiti": "🇭🇹", "Honduras": "🇭🇳", "Hong Kong": "🇭🇰", "Hungary": "🇭🇺",
    "Iceland": "🇮🇸", "India": "🇮🇳", "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶",
    "Ireland": "🇮🇪", "Israel": "🇮🇱", "Italy": "🇮🇹", "IVORY COAST": "🇨🇮", "Ivory Coast": "🇨🇮", "Jamaica": "🇯🇲",
    "Japan": "🇯🇵", "Jordan": "🇯🇴", "Kazakhstan": "🇰🇿", "Kenya": "🇰🇪", "Kuwait": "🇰🇼",
    "Kyrgyzstan": "🇰🇬", "Laos": "🇱🇦", "Latvia": "🇱🇻", "Lebanon": "🇱🇧", "Liberia": "🇱🇷",
    "Libya": "🇱🇾", "Lithuania": "🇱🇹", "Luxembourg": "🇱🇺", "Madagascar": "🇲🇬", "Malaysia": "🇲🇾",
    "Mali": "🇲🇱", "Malta": "🇲🇹", "Mexico": "🇲🇽", "Moldova": "🇲🇩", "Monaco": "🇲🇨",
    "Mongolia": "🇲🇳", "Montenegro": "🇲🇪", "Morocco": "🇲🇦", "Mozambique": "🇲🇿", "Myanmar": "🇲🇲",
    "Namibia": "🇳🇦", "Nepal": "🇳🇵", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿", "Nicaragua": "🇳🇮",
    "Niger": "🇳🇪", "Nigeria": "🇳🇬", "North Korea": "🇰🇵", "North Macedonia": "🇲🇰", "Norway": "🇳🇴",
    "Oman": "🇴🇲", "Pakistan": "🇵🇰", "Panama": "🇵🇦", "Paraguay": "🇵🇾", "Peru": "🇵🇪",
    "Philippines": "🇵🇭", "Poland": "🇵🇱", "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Romania": "🇷🇴",
    "Russia": "🇷🇺", "Rwanda": "🇷🇼", "Saudi Arabia": "🇸🇦", "Senegal": "🇸🇳", "Serbia": "🇷🇸",
    "Sierra Leone": "🇸🇱", "Singapore": "🇸🇬", "Slovakia": "🇸🇰", "Slovenia": "🇸🇮", "Somalia": "🇸🇴",
    "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Spain": "🇪🇸", "Sri Lanka": "🇱🇰", "Sudan": "🇸🇩",
    "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Syria": "🇸🇾", "Taiwan": "🇹🇼", "Tajikistan": "🇹🇯",
    "Tanzania": "🇹🇿", "Thailand": "🇹🇭", "TOGO": "🇹🇬", "Tunisia": "🇹🇳", "Turkey": "🇹🇷",
    "Turkmenistan": "🇹🇲", "Uganda": "🇺🇬", "Ukraine": "🇺🇦", "United Arab Emirates": "🇦🇪", "United Kingdom": "🇬🇧",
    "United States": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿", "Venezuela": "🇻🇪", "Vietnam": "🇻🇳",
    "Yemen": "🇾🇪", "Zambia": "🇿🇲", "Zimbabwe": "🇿🇼", "Unknown Country": "🏴‍☠️"
}

SERVICE_KEYWORDS = {
    "Facebook": ["facebook"], "Google": ["google", "gmail"], "WhatsApp": ["whatsapp"],
    "Telegram": ["telegram"], "Instagram": ["instagram"], "Amazon": ["amazon"],
    "Netflix": ["netflix"], "LinkedIn": ["linkedin"], "Messenger": ["messenger", "meta"],
    "TikTok": ["tiktok"], "Discord": ["discord"], "PayPal": ["paypal"],
    "Binance": ["binance"], "Uber": ["uber"], "Spotify": ["spotify"],
    "Tinder": ["tinder"], "Line": ["line"], "Viber": ["viber"], "Unknown": ["unknown"]
}

SERVICE_EMOJIS = {
    "Telegram": "📩", "WhatsApp": "🟢", "Facebook": "📘", "Instagram": "📸", "Messenger": "💬",
    "Google": "🔍", "Gmail": "✉️", "YouTube": "▶️", "Twitter": "🐦", "X": "❌",
    "TikTok": "🎵", "Snapchat": "👻", "Amazon": "🛒", "PayPal": "💰", "Unknown": "❓"
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
    with open(STATE_FILE, 'w') as f: json.dump(processed_ids, f)

# --- Telegram Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if str(user_id) in ADMIN_CHAT_IDS:
        await update.message.reply_text("Welcome Admin!\n/add_chat <id>\n/remove_chat <id>\n/list_chats")
    else:
        await update.message.reply_text("Unauthorized.")

async def add_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_CHAT_IDS: return
    try:
        new_id = context.args[0]
        cids = load_chat_ids()
        if new_id not in cids:
            cids.append(new_id)
            save_chat_ids(cids)
            await update.message.reply_text(f"✅ Added: {new_id}")
    except: await update.message.reply_text("Format: /add_chat <id>")

async def list_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_CHAT_IDS: return
    cids = load_chat_ids()
    msg = "📜 Registered Chats:\n" + "\n".join([f"- `{escape_markdown(c)}`" for c in cids])
    await update.message.reply_text(msg, parse_mode='MarkdownV2')

# --- Main API Fetching ---
async def fetch_sms_from_api(client, headers, csrf_token):
    all_messages = []
    try:
        today = datetime.utcnow()
        start_date = today - timedelta(days=1)
        from_date_str, to_date_str = start_date.strftime('%m/%d/%Y'), today.strftime('%m/%d/%Y')
        
        # Initial post to get groups
        payload = {'from': from_date_str, 'to': to_date_str, '_token': csrf_token}
        res = await client.post(SMS_API_ENDPOINT, headers=headers, data=payload)
        soup = BeautifulSoup(res.text, 'html.parser')
        group_divs = soup.find_all('div', {'class': 'pointer'})
        
        for div in group_divs:
            onclick = div.get('onclick', '')
            match = re.search(r"getDetials\('(.+?)'\)", onclick)
            if not match: continue
            group_id = match.group(1)
            
            # Fetch numbers in group
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
                        
                        code_match = re.search(r'(\d{3}-\d{3})', sms_text) or re.search(r'\b(\d{4,8})\b', sms_text)
                        code = code_match.group(1) if code_match else "N/A"
                        
                        all_messages.append({
                            "id": f"{phone_number}-{sms_text}",
                            "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
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
                        await context.bot.send_message(chat_id=cid, text=full_msg, parse_mode='MarkdownV2')
                    save_processed_id(msg["id"])
        except Exception: print(traceback.format_exc())

def main():
    app = Application.builder().token(YOUR_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("add_chat", add_chat_command))
    app.add_handler(CommandHandler("list_chats", list_chats_command))
    
    app.job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=1)
    print("🤖 Bot Online...")
    app.run_polling()

if __name__ == "__main__":
    main()

