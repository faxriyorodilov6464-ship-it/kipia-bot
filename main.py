import os
import sys

# Auto-correct working directory for Render
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

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
    return "Fast KIPiA Tag Finder is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web_server).start()
# ------------------------------------------

# Bot Token
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

# Global memory cache for incredibly fast searching
CACHED_DATA = []

def clean_val(val):
    """Clean empty values or placeholders in Excel cells"""
    if pd.isna(val) or str(val).strip() in ['-', '—', 'nan', 'N/A', 'NA', '_', '', 'nan/nan', 'None']:
        return "—"
    return str(val).strip()

def preload_excel_databases():
    """Load all Excel sheets into RAM once when the bot starts up"""
    global CACHED_DATA
    CACHED_DATA = []
    
    files = glob.glob("*.xlsx") + glob.glob("*.xls")
    print(f"📦 Preloading databases: {files}")
    
    for file in files:
        try:
            file_name_short = os.path.basename(file)
            excel_file = pd.ExcelFile(file)
            
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name, header=None)
                header_row = df.iloc[0] if len(df) > 1 else None
                
                # Cache rows for instant lookup
                for idx, row in df.iterrows():
                    row_values = row.astype(str).values
                    row_text_combined = "".join(row_values).upper()
                    clean_row_text = re.sub(r'[-_\s]', '', row_text_combined)
                    
                    # Store row matrix structures safely in memory
                    CACHED_DATA.append({
                        "clean_text": clean_row_text,
                        "file_name": file_name_short,
                        "sheet_name": sheet_name,
                        "row_data": list(row),
                        "header_row": list(header_row) if header_row is not None else None
                    })
        except Exception as e:
            print(f"❌ Error preloading {file}: {e}")
            continue
    print(f"✅ Successfully cached {len(CACHED_DATA)} rows.")

def search_instrument_tag_fast(search_query):
    search_query = str(search_query).strip().upper()
    clean_query = re.sub(r'[-_\s]', '', search_query)
    
    if not CACHED_DATA:
        preload_excel_databases()
        if not CACHED_DATA:
            return ["⚠️ Database is empty or no files found on the server!"]
            
    results = []
    
    for item in CACHED_DATA:
        if clean_query in item["clean_text"]:
            # Format results in a clean, simple, and elegant plain text layout
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
                if item["header_row"] is not None:
                    possible_label = str(item["header_row"][col_idx]).strip()
                    if possible_label and possible_label != 'nan' and possible_label != str(cell_value):
                        attr_name = possible_label
                
                info_lines.append(f"🔹 {attr_name}: {val_str}")
            
            results.append("\n".join(info_lines))
            
    return list(set(results))

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardRemove(selective=False)
    bot.reply_to(
        message, 
        "Welcome to Smart KIPiA Search Bot!\n\nPlease enter the KIP TAG number to search across all databases (e.g., PT-1103, LICA-10101, or II-B22303):",
        reply_markup=markup
    )

@bot.message_handler(commands=['reload'])
def manual_reload(message):
    bot.reply_to(message, "🔄 Reloading Excel files into memory cache...")
    preload_excel_databases()
    bot.send_message(message.chat.id, "✅ Memory cache updated successfully!")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text.strip()
    
    if len(text) >= 3: 
        results = search_instrument_tag_fast(text)
        
        if results:
            for result in results:
                # Removed parse_mode="Markdown" to ensure it uses the clean, beautiful system font
                bot.send_message(message.chat.id, result)
        else:
            bot.send_message(message.chat.id, f"❌ Match for '{text}' not found in any database.")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter at least 3 characters to search.")

if __name__ == '__main__':
    preload_excel_databases()
    bot.infinity_polling()
