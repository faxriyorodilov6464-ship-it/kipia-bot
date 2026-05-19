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
    """Server ichidagi faqat kerakli Excel fayllarini topish"""
    excel_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        if '.venv' in root or '.git' in root:
            continue
        for file in files:
            if file.lower().endswith(('.xlsx', '.xls')):
                excel_files.append(os.path.join(root, file))
    return excel_files

def preload_excel_databases():
    """Sariq rangli ustun nomlarini (Headers) hisobga olib bazani RAMga yuklash"""
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
                # header=None qilib o'qiymiz, keyin sariq qatorni o'zimiz qidirib topamiz
                df = excel_file.parse(sheet_name, header=None)
                if df.empty:
                    continue
                
                # Sariq sarlavha qatori odatda 0, 1 yoki 2-qatorda bo'ladi (ichida 'iom tag' yoki 'field tag' borini qidiramiz)
                header_row_index = 0
                for idx, row in df.head(5).iterrows():
                    row_str = " ".join([str(x).lower() for x in row.values])
                    if 'iom tag' in row_str or 'field tag' in row_str or 'description' in row_str:
                        header_row_index = idx
                        break
                
                # Sarlavha nomlarini tozalab listga olamiz
                headers = [str(x).strip().upper() for x in df.iloc[header_row_index].values]
                
                # Ma'lumotlarni faqat sarlavhadan keyingi qatorlardan boshlab o'qiymiz
                data_df = df.iloc[header_row_index + 1:]
                
                for index, row in data_df.iterrows():
                    row_values = [clean_val(x) for x in row.values]
                    
                    if any(x != "-" for x in row_values):
                        # Ustun nomi va uning qiymatini juftlik qilib Dict yaratamiz
                        row_dict = {}
                        for h_idx, h_name in enumerate(headers):
                            if h_idx < len(row_values):
                                row_dict[h_name] = row_values[h_idx]
                        
                        # Qidiruv oson bo'lishi uchun hamma matnni bitta qatorga yig'amiz
                        full_text_search = " ".join(row_values).lower()
                        
                        CACHED_DATA.append({
                            'sheet': sheet_name,
                            'search_text': full_text_search,
                            'data': row_dict
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
        
    # Faqat birinchi 3 ta mos kelgan natijani chiroyli blokda chiqaramiz
    for res in results[:3]:
        d = res['data']
        
        # Sariq jadvalingizdagi ustun nomlariga qarab ma'lumotlarni ajratamiz
        tag_no = d.get('FIELD TAG', d.get('IOM TAG', message.text.upper()))
        if tag_no == "-": 
            tag_no = d.get('IOM TAG', message.text.upper())
            
        iom = d.get('IOM TAG', '-')
        rack = res['sheet']
        ch = d.get('CHANNEL NO', d.get('CH NO', '-'))
        
        cabinet = d.get('SYSTEM CABINET', d.get('CABINET', '-'))
        controller = d.get('CONTROLLER', '-')
        description = d.get('DESCRIPTION', 'KIPiA Device')
        
        device_type = d.get('IOM TYPE', '-')
        signal_type = d.get('2/4 WIRE', d.get('POWER SUPPLY', '4~20mA'))
        
        # JB va Klema ma'lumotlari (agar jadvalda JB yoki TB ustunlari bo'lsa)
        ftb_cabinet = d.get('FTB NO', d.get('P&ID NO', '-'))
        tb_no = d.get('TB1', d.get('TB NO', '-'))
        tb2_no = d.get('TB2', '-')
        
        # Siz xohlagan professional inglizcha dizayn formati (ortiqcha so'zlarsiz):
        response_text = f"🔹 *{tag_no}*\n"
        response_text += f"IOM: {iom} | Rack: {rack} | CH: {ch}\n"
        response_text += "-----------------------------------------\n"
        response_text += f"Cabinet: {cabinet} | Controller: {controller}\n"
        response_text += f"*{description}*\n\n"
        
        response_text += f"  • *Device Type:* {device_type}\n"
        response_text += f"  • *Signal Type:* {signal_type}\n"
        response_text += f"  • *Cabinet FTB:* {ftb_cabinet} | *TB:* {tb_no}\n"
        
        if tb2_no != "-":
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
print("🚀 Professional KIPiA Bot is running...")
bot.infinity_polling()
