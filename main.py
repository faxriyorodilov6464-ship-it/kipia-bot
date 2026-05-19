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
    return "KIPiA Case-Insensitive Finder is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web_server).start()
# ------------------------------------------

# Bot Token
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

# Global xotira kesh
CACHED_DATA = []

def clean_val(val):
    """Excel kataklaridagi bo'sh yoki keraksiz belgilarni tozalash"""
    if pd.isna(val) or str(val).strip() in ['-', '—', 'nan', 'N/A', 'NA', '_', '', 'nan/nan', 'None']:
        return "—"
    return str(val).strip()

def find_all_excel_files():
    """Server ichidagi barcha Excel fayllarni (katta-kichik harflarga qaramasdan) qidirib topish"""
    excel_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            # .xlsx, .xlsx, .xls, .XLS, .Xlsx formatlarning hammasini qabul qiladi
            if file.lower().endswith(('.xlsx', '.xls')):
                full_path = os.path.join(root, file)
                excel_files.append(full_path)
    return excel_files

def preload_excel_databases():
    """Barcha topilgan Excel fayllarni RAM xotirasiga mukammal yuklash"""
    global CACHED_DATA
    CACHED_DATA = []
    
    files = find_all_excel_files()
    print(f"📦 Topilgan barcha Excel fayllar ro'yxati: {files}")
    
    if not files:
        print("⚠️ DIQQAT: Server ichida birorta ham Excel fayl topilmadi!")
        return

    for file in files:
        file_name_short = os.path.basename(file)
        try:
            # Fayl formati qanday yozilgan bo'lishidan qat'iy nazar to'g'ri engine tanlash
            if file_name_short.lower().endswith('.xls'):
                excel_file = pd.ExcelFile(file, engine='xlrd')
            else:
                excel_file = pd.ExcelFile(file)
            
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name, header=None)
                
                if df.empty:
                    continue
                
                # Sarlavha (Header) qatorini aniqlashga urinish
                header_row = None
                for i in range(min(5, len(df))):
                    row_str = "".join(df.iloc[i].astype(str).values).upper()
                    if "TAG" in row_str or "DESCRIPTION" in row_str or "CABINET" in row_str:
                        header_row = list(df.iloc[i])
                        break
                
                if header_row is None and len(df) > 0:
                    header_row = list(df.iloc[0])

                # Har bir satrni xotiraga joylash
                for idx, row in df.iterrows():
                    row_data_list = list(row)
                    row_text_combined = "".join(row.astype(str).values).upper()
                    clean_row_text = re.sub(r'[-_\s]', '', row_text_combined)
                    
                    CACHED_DATA.append({
                        "clean_text": clean_row_text,
                        "file_name": file_name_short,
                        "sheet_name": sheet_name,
                        "row_data": row_data_list,
                        "header_row": header_row
                    })
        except Exception as e:
            print(f"❌ Faylni o'qishda xatolik {file_name_short}: {e}")
            continue
            
    print(f"✅ Yuklash yakunlandi. Jami keshga olingan satrlar: {len(CACHED_DATA)}")

def search_instrument_tag_fast(search_query):
    search_query = str(search_query).strip().upper()
    clean_query = re.sub(r'[-_\s]', '', search_query)
    
    if not CACHED_DATA:
        preload_excel_databases()
        if not CACHED_DATA:
            return ["⚠️ Baza fayllari o'qilmadi yoki serverda Excel fayllar topilmadi. Qayta urinish uchun /reload buyrug'ini bosing."]
            
    results = []
    
    for item in CACHED_DATA:
        if clean_query in item["clean_text"]:
            info_lines = [
                f"📊 DATABASE: {item['file_name']}",
                f"📄 Sheet: {item['sheet_name']}",
                "———————————————"
            ]
            
            for col_idx, cell_value in enumerate(item["row_data"]):
                val_str = clean_val(cell_value)
                if val_str == "—":
                    continue
                
                attr_name = f"Column {col_idx + 1}"
                if item["header_row"] is not None and col_idx < len(item["header_row"]):
                    possible_label = str(item["header_row"][col_idx]).strip()
                    if possible_label and possible_label != 'nan' and possible_label != str(cell_value):
                        attr_name = possible_label
                
                attr_name = re.sub(r'[*_`\[\]]', '', attr_name)
                val_str = re.sub(r'[*_`\[\]]', '', val_str)
                
                info_lines.append(f"🔹 {attr_name}: {val_str}")
            
            results.append("\n".join(info_lines))
            
    return list(set(results))

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardRemove(selective=False)
    bot.reply_to(
        message, 
        "Welcome to Smart KIPiA Search Bot!\n\nEnter KIP TAG number to search across all databases:",
        reply_markup=markup
    )

@bot.message_handler(commands=['reload'])
def manual_reload(message):
    bot.reply_to(message, "🔄 Reloading Excel files into memory cache...")
    preload_excel_databases()
    if CACHED_DATA:
        bot.send_message(message.chat.id, f"✅ Xotira muvaffaqiyatli yangilandi! Jami yuklangan ma'lumotlar soni: {len(CACHED_DATA)}")
    else:
        current_dir_content = os.listdir(BASE_DIR)
        bot.send_message(message.chat.id, f"⚠️ Kesh baribir bo'sh. Kataloq tarkibi: {current_dir_content}")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text.strip()
    
    if len(text) >= 3: 
        results = search_instrument_tag_fast(text)
        
        if results:
            for result in results:
                bot.send_message(message.chat.id, result)
        else:
            bot.send_message(message.chat.id, f"❌ '{text}' bo'yicha hech qanday ma'lumot topilmadi.")
    else:
        bot.send_message(message.chat.id, "⚠️ Qidirish uchun kamida 3 ta belgi kiriting.")

if __name__ == '__main__':
    preload_excel_databases()
    bot.infinity_polling()
