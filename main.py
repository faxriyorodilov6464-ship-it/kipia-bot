import os
import sys

# Server ishchi muhitini sozlash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

from flask import Flask
from threading import Thread
import pandas as pd
import glob
import telebot

# --- WEB SERVER FOR RENDER PORT BINDING ---
app = Flask('')

@app.route('/')
def home():
    return "Smart KIPiA Finder is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web_server).start()
# ------------------------------------------

# Bot Token
BOT_TOKEN = "8896826475:AAE_Z0W7Rhm6ynHH2a0smKjTyvXjW9GlLFM"
bot = telebot.TeleBot(BOT_TOKEN)

# Global xotira keshi
CACHED_DATA = []

def clean_val(val):
    """Kataklardagi bo'sh belgilarni tozalash"""
    if pd.isna(val) or str(val).strip() in ['-', '~', 'nan', 'N/A', 'NA', '.', '', 'nan/nan', 'None']:
        return "-"
    return str(val).strip()

def find_all_excel_files():
    """Server ichidagi barcha Excel fayllarini topish"""
    excel_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        if '.venv' in root or '.git' in root:
            continue
        for file in files:
            if file.lower().endswith(('.xlsx', '.xls')):
                excel_files.append(os.path.join(root, file))
    return excel_files

def preload_excel_databases():
    """Ustunlarni 100% aniqlik bilan bog'lab RAMga yuklash"""
    global CACHED_DATA
    CACHED_DATA = []
    
    files = find_all_excel_files()
    if not files:
        return "⚠️ No Excel files found on the server!"
        
    loaded_count = 0
    for file in files:
        file_name_short = os.path.basename(file)
        try:
            if file_name_short.lower().endswith('.xls'):
                excel_file = pd.ExcelFile(file, engine='xlrd')
            else:
                excel_file = pd.ExcelFile(file, engine='openpyxl')
                
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name, header=None)
                if df.empty:
                    continue
                
                # Sariq sarlavha qatorini (Headers) aniqlash (1-8 qatorlar orasidan)
                header_row_index = 0
                for idx, row in df.head(8).iterrows():
                    row_str = " ".join([str(x).lower() for x in row.values])
                    if 'tag' in row_str or 'description' in row_str or 'cabinet' in row_str or 'type' in row_str:
                        header_row_index = idx
                        break
                
                # Sarlavhalarni kichik harfda va toza formatda olamiz
                headers = [str(x).strip().lower() for x in df.iloc[header_row_index].values]
                
                # Ma'lumotlar sarlavhadan keyingi qatordan boshlanadi
                data_df = df.iloc[header_row_index + 1:]
                
                for index, row in data_df.iterrows():
                    row_values = [clean_val(x) for x in row.values]
                    
                    if any(x != "-" for x in row_values):
                        row_dict = {}
                        for h_idx, h_name in enumerate(headers):
                            if h_idx < len(row_values):
                                row_dict[h_name] = row_values[h_idx]
                        
                        full_text_search = " ".join(row_values).lower()
                        
                        CACHED_DATA.append({
                            'file': file_name_short,
                            'sheet': sheet_name,
                            'search_text': full_text_search,
                            'data': row_dict,
                            'raw_list': row_values
                        })
                        loaded_count += 1
        except Exception as e:
            print(f"❌ Error reading {file_name_short}: {e}")
            
    return f"✅ Database successfully updated!\n📊 Total rows loaded: {loaded_count}"

try:
    preload_excel_databases()
except Exception as e:
    print(f"Initial load error: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Smart KIPiA Search Bot!\n\nEnter KIP TAG number to search across all databases:")

@bot.message_handler(commands=['reload'])
def reload_cache(message):
    bot.reply_to(message, "🔄 Reloading Excel files into memory cache...")
    status_msg = preload_excel_databases()
    bot.reply_to(message, status_msg)

@bot.message_handler(func=lambda message: True)
def search_tag(message):
    query = message.text.strip().lower()
    
    if len(query) < 2:
        bot.reply_to(message, "⚠️ Please enter at least 2 characters for search!")
        return
        
    if not CACHED_DATA:
        bot.reply_to(message, "⚠️ Database cache is empty! Please run /reload command.")
        return
        
    results = []
    for item in CACHED_DATA:
        if query in item['search_text']:
            results.append(item)
            
    if not results:
        bot.reply_to(message, f"🔍 No data found for '{message.text}'.")
        return
        
    for res in results[:3]:
        d = res['data']
        raw = res['raw_list']
        
        # --- BARCHA JADVAL VARIANTLARINI TEKSHIRADIGAN AQLLI FILTR ---
        
        # 1. FIELD TAG (Datchik nomi)
        tag_no = "-"
        for k, v in d.items():
            if 'field tag' in k or 'device tag' in k or 'tag no' in k or 'tag_no' in k or 'datchik' in k:
                if v != "-": tag_no = v; break
        if tag_no == "-":
            for k, v in d.items():
                if 'iom tag' in k or 'dcs tag' in k or 'tag' in k:
                    if v != "-": tag_no = v; break
        if tag_no == "-": tag_no = message.text.upper()

        # 2. IOM TAG
        iom = "-"
        for k, v in d.items():
            if 'iom tag' in k or 'module tag' in k or 'iom_tag' in k: 
                if v != "-": iom = v; break
        if iom == "-" and len(raw) > 3: iom = raw[3] # Zaxira reja

        # 3. CHANNEL NO
        ch = "-"
        for k, v in d.items():
            if 'channel' in k or 'ch no' in k or 'ch_no' in k or 'ch.' in k or 'kun' in k: 
                if v != "-": ch = v; break
        if ch == "-" and len(raw) > 10: ch = raw[10] # Zaxira reja

        # 4. SYSTEM CABINET
        cabinet = "-"
        for k, v in d.items():
            if 'system cabinet' in k or 'cabinet' in k or 'panel' in k or 'shkaf' in k or 'cab' in k: 
                if v != "-": cabinet = v; break
        if cabinet == "-" and len(raw) > 8: cabinet = raw[8] # Zaxira reja

        # 5. CONTROLLER
        controller = "-"
        for k, v in d.items():
            if 'controller' in k or 'cpu' in k or 'kontrol' in k: 
                if v != "-": controller = v; break
        if controller == "-" and len(raw) > 9: controller = raw[9] # Zaxira reja

        # 6. DESCRIPTION (Izoh)
        description = "-"
        for k, v in d.items():
            if 'description' in k or 'service' in k or 'izoh' in k or 'nomi' in k: 
                if v != "-": description = v; break
        if description == "-" and len(raw) > 7: description = raw[7] # Zaxira reja
        if description == "-": description = "KIPiA Device"

        # 7. DEVICE TYPE
        device_type = "-"
        for k, v in d.items():
            if 'iom type' in k or 'device type' in k or 'type' in k or 'tur' in k: 
                if v != "-": device_type = v; break
        if device_type == "-" and len(raw) > 1: device_type = raw[1] # Zaxira reja
            
        # 8. SIGNAL TYPE
        signal_type = "-"
        for k, v in d.items():
            if 'wire' in k or 'signal' in k or 'power supply' in k: 
                if v != "-": signal_type = v; break
        if signal_type == "-": signal_type = "4~20mA"

        # 9. CABINET FTB (Marshrut qutisi yoki P&ID)
        ftb_cabinet = "-"
        for k, v in d.items():
            if 'ftb' in k or 'p&id' in k or 'pid' in k or 'jb' in k: 
                if v != "-": ftb_cabinet = v; break
        if ftb_cabinet == "-" and len(raw) > 4: ftb_cabinet = raw[4] # Zaxira reja
            
        # 10. TERMINAL BLOKLAR (TB1 va TB2)
        tb_no = "-"
        for k, v in d.items():
            if 'tb1' in k or 'tb no' in k or 'terminal 1' in k or 'klema' in k: 
                if v != "-": tb_no = v; break
        if tb_no == "-" and len(raw) > 11: tb_no = raw[11] # Zaxira reja
            
        tb2_no = "-"
        for k, v in d.items():
            if 'tb2' in k or 'return' in k or 'terminal 2' in k: 
                if v != "-": tb2_no = v; break
        if tb2_no == "-" and len(raw) > 12: tb2_no = raw[12] # Zaxira reja

        # --- PROFESSIONAL TAGMA-TAG MATN FORMATI ---
        response_text = f"🔹 *{tag_no}*\n"
        response_text += f"IOM: {iom} | Rack: {res['sheet']} | CH: {ch}\n"
        response_text += "-----------------------------------------\n"
        response_text += f"Cabinet: {cabinet} | Controller: {controller}\n"
        response_text += f"*{description}*\n\n"
        
        response_text += f"  • *Device Type:* {device_type}\n"
        response_text += f"  • *Signal Type:* {signal_type}\n"
        response_text += f"  • *Cabinet FTB:* {ftb_cabinet} | *TB:* {tb_no}\n"
        
        if tb2_no != "-" and tb2_no != "0":
            response_text += f"  • *TB2 / Return:* {tb2_no}\n"
            
        response_text += "\n=========================\n"
        
        try:
            bot.send_message(message.chat.id, response_text, parse_mode="Markdown")
        except Exception:
            clean_text = response_text.replace("*", "")
            bot.send_message(message.chat.id, clean_text)
            
    if len(results) > 3:
        bot.send_message(message.chat.id, f"⚠️ Found {len(results)} matches. Showing first 3. Please clarify your query.")

# Botni ishga tushirish
print("🚀 Ultra Smart Adaptive KIPiA Bot is running...")
bot.infinity_polling()
