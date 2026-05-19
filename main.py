import os
import sys

# Absolute path correction for Render stability
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
    return "KIPiA Absolute Finder is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web_server).start()
# ------------------------------------------

# Bot Token
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

# Global memory cache
CACHED_DATA = []

def clean_val(val):
    """Clean empty values or placeholders in Excel cells"""
    if pd.isna(val) or str(val).strip() in ['-', '—', 'nan', 'N/A', 'NA', '_', '', 'nan/nan', 'None']:
        return "—"
    return str(val).strip()

def preload_excel_databases():
    """Load all Excel formats properly into RAM using absolute path resolution"""
    global CACHED_DATA
    CACHED_DATA = []
    
    # Secure absolute path lookups for Render environment
    search_path_xlsx = os.path.join(BASE_DIR, "*.xlsx")
    search_path_xls = os.path.join(BASE_DIR, "*.xls")
    
    files = glob.glob(search_path_xlsx) + glob.glob(search_path_xls)
    print(f"📦 Preloading databases from {BASE_DIR}: {files}")
    
    if not files:
        print("⚠️ WARNING: No Excel files detected in directory root!")
        return

    for file in files:
        try:
            file_name_short = os.path.basename(file)
            
            if file_name_short.lower().endswith('.xls'):
                excel_file = pd.ExcelFile(file, engine='xlrd')
            else:
                excel_file = pd.ExcelFile(file)
            
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name, header=None)
                
                if df.empty:
                    continue
                
                header_row = None
                for i in range(min(5, len(df))):
                    row_str = "".join(df.iloc[i].astype(str).values).upper()
                    if "TAG" in row_str or "DESCRIPTION" in row_str or "CABINET" in row_str:
                        header_row = list(df.iloc[i])
                        break
                
                if header_row is None and len(df) > 0:
                    header_row = list(df.iloc[0])

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
            print(f"❌ Error preloading {file}: {e}")
            continue
    print(f"✅ Preload finished. Total rows cached: {len(CACHED_DATA)}")

def search_instrument_tag_fast(search_query):
    search_query = str(search_query).strip().upper()
    clean_query = re.sub(r'[-_\s]', '', search_query)
    
    if not CACHED_DATA:
        preload_excel_databases()
        if not CACHED_DATA:
            return ["⚠️ Database files could not be read or are missing from the server. Please run /reload"]
            
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
        "Welcome to Smart KIPiA Search Bot!\n\nPlease enter the KIP TAG number to search across all databases:",
        reply_markup=markup
    )

@bot.message_handler(commands=['reload'])
def manual_reload(message):
    bot.reply_to(message, "🔄 Reloading Excel files into memory cache...")
    preload_excel_databases()
    if CACHED_DATA:
        bot.send_message(message.chat.id, f"✅ Memory cache updated successfully! Total loaded rows: {len(CACHED_DATA)}")
    else:
        bot.send_message(message.chat.id, "⚠️ Active reload finished but cache is still empty. Check server files.")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text.strip()
    
    if len(text) >= 3: 
        results = search_instrument_tag_fast(text)
        
        if results:
            for result in results:
                bot.send_message(message.chat.id, result)
        else:
            bot.send_message(message.chat.id, f"❌ Match for '{text}' not found in any database.")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter at least 3 characters to search.")

if __name__ == '__main__':
    preload_excel_databases()
    bot.infinity_polling()
