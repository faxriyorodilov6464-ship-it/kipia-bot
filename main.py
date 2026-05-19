import os
import sys

# Server ildiz katalogini aniqlash va ishchi muhitni sozlash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

from flask import Flask
from threading import Thread
import pandas as pd
import glob
import re
import telebot

# --- WEB SERVER FOR RENDER PORT BINDING ---
app = Flask('')

@app.route('/')
def home():
    return "KIPIA Case-Insensitive Finder is Running!"

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
    """Excel kataklaridagi bo'sh yoki keraksiz belgilarni tozalash"""
    if pd.isna(val) or str(val).strip() in ['-', '~', 'nan', 'N/A', 'NA', '.', '', 'nan/nan', 'None']:
        return "-"
    return str(val).strip()

def find_all_excel_files():
    """Server ichidagi faqat kerakli Excel fayllarini qidirib topish (.venv va .git chetlab o'tiladi)"""
    excel_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        # Tizim ichki konfiguratsiya papkalariga kirib ketmasligi uchun ularni chetlab o'tamiz
        if '.venv' in root or '.git' in root:
            continue
            
        for file in files:
            if file.lower().endswith(('.xlsx', '.xls')):
                full_path = os.path.join(root, file)
                excel_files.append(full_path)
    return excel_files

def preload_excel_databases():
    """Barcha topilgan Excel fayllarni RAM xotirasiga mukammal yuklash"""
    global CACHED_DATA
    CACHED_DATA = []
    
    files = find_all_excel_files()
    print(f"📂 Topilgan barcha Excel fayllar ro'yxati: {files}")
    
    if not files:
        print("⚠️ DIQQAT: Server ichida birorta ham Excel fayl topilmadi!")
        return f"⚠️ Server ichida birorta ham Excel fayl topilmadi! Katalog tarkibi: {os.listdir(BASE_DIR)}"
        
    loaded_count = 0
    for file in files:
        file_name_short = os.path.basename(file)
        try:
            # Fayl formatiga qarab to'g'ri engine tanlash
            if file_name_short.lower().endswith('.xls'):
                excel_file = pd.ExcelFile(file, engine='xlrd')
            else:
                excel_file = pd.ExcelFile(file, engine='openpyxl')
                
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name, header=None)
                
                if df.empty:
                    continue
                    
                df = df.astype(str)
                for index, row in df.iterrows():
                    row_values = [clean_val(x) for x in row.values]
                    # Agar qatorda umuman ma'lumot bo'lsa xotiraga qo'shamiz
                    if any(x != "-" for x in row_values):
                        row_text = " | ".join(row_values).lower()
                        CACHED_DATA.append({
                            'filename': file_name_short,
                            'sheet': sheet_name,
                            'text': row_text,
                            'original_row': row_values
                        })
                        loaded_count += 1
        except Exception as e:
            print(f"❌ {file_name_short} faylini o'qishda xato: {e}")
            
    return f"✅ Kesh muvaffaqiyatli yangilandi!\n📊 Jami yuklangan satrlar soni: {loaded_count}\n📁 O'qilgan fayllar: {list(set([d['filename'] for d in CACHED_DATA]))}"

# Server yoqilishi bilan bazani bir marta avtomatik yuklashga urinish
try:
    preload_excel_databases()
except Exception as e:
    print(f"Dastlabki yuklashda xato: {e}")

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
        bot.reply_to(message, "⚠️ Qidiruv uchun kamida 2 ta belgi kiriting!")
        return
        
    if not CACHED_DATA:
        bot.reply_to(message, "⚠️ Xotira kesh bo'sh! Iltimos, /reload buyrug'ini bosing.")
        return
        
    results = []
    for item in CACHED_DATA:
        if query in item['text']:
            results.append(item)
            
    if not results:
        bot.reply_to(message, f"🔍 '{message.text}' bo'yicha hech qanday ma'lumot topilmadi.")
        return
        
    # Maksimal 10 ta natijani chiqarish (Telegram chekloviga tushmaslik uchun)
    response_text = f"🔍 Topilgan natijalar ({len(results)} ta):\n\n"
    for idx, res in enumerate(results[:10], 1):
        response_text += f"📄 *Fayl:* {res['filename']} ({res['sheet']})\n"
        # Tozalangan qatorni chiroyli ko'rinishga keltirish
        clean_row = [val for val in res['original_row'] if val != "-"]
        response_text += f"📝 *Ma'lumot:* {', '.join(clean_row)}\n"
        response_text += "-------------------------\n"
        
    if len(results) > 10:
        response_text += f"⚠️ Yana {len(results) - 10} ta natija bor, iltimos qidiruvni aniqlashtiring."
        
    try:
        bot.reply_to(message, response_text, parse_mode="Markdown")
    except Exception:
        # Agar Markdown formatda xato bersa, oddiy matnda yuborish
        bot.reply_to(message, response_text.replace("*", ""))

# Botni uzluksiz yurgizish
print("🚀 Bot muvaffaqiyatli ishga tushdi...")
bot.infinity_polling()
