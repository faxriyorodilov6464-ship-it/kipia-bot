import os
import sys

# Auto-correct working directory for Render/Pydroid
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
    return "KIPiA Search Bot is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web_server).start()
# ------------------------------------------

# Bot Token
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

def clean_val(val):
    """Clean empty values or placeholders in Excel cells"""
    if pd.isna(val) or str(val).strip() in ['-', '—', 'nan', 'N/A', 'NA', '_', '', 'nan/nan']:
        return "—"
    return str(val).strip()

def search_instrument_tag(search_query):
    search_query = str(search_query).strip().upper()
    # Normalize query by removing spaces, dashes, and underscores
    clean_query = re.sub(r'[-_\s]', '', search_query)
    
    results = []
    
    # Search for all Excel files in the directory
    files = glob.glob("*.xlsx") + glob.glob("*.xls")
    
    if not files:
        return ["⚠️ No Excel database files (.xlsx/.xls) found on the server!"]

    for file in files:
        try:
            file_upper = file.upper()
            file_name_short = os.path.basename(file)
            
            excel_file = pd.ExcelFile(file)
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)
                
                # Dynamic column mapping by clearing space and converting to uppercase
                orig_cols = list(df.columns)
                clean_cols = [str(c).strip().upper() for c in orig_cols]
                df.columns = clean_cols
                
                # Identify columns that might contain TAGs based on common keywords
                tag_cols = []
                for idx, col in enumerate(clean_cols):
                    if any(kwd in col for kwd in ['TAG', 'LOOP', '1617', 'DEVICE', 'IDENTIFIER']):
                        tag_cols.append(orig_cols[idx]) # Store the original column name case
                
                # If no specific tag column is matched, search across ALL columns in the sheet
                if not tag_cols:
                    tag_cols = orig_cols
                
                for actual_col in tag_cols:
                    # Temporary series for cleaned search column to avoid mismatch
                    clean_series = df[actual_col.strip().upper()].astype(str).str.upper().str.replace(r'[-_\s]', '', regex=True)
                    matched_rows = df[clean_series.str.contains(clean_query, na=False)]
                    
                    if not matched_rows.empty:
                        for _, row in matched_rows.iterrows():
                            # Re-map row keys to search standard fields flexibly
                            row_dict = {orig_cols[i]: row[clean_cols[i]] for i in range(len(orig_cols))}
                            
                            info_lines = [f"📊 **DATABASE:** `{file_name_short}` | **Sheet:** `{sheet_name}`"]
                            
                            # Extract crucial details dynamically based on contains match
                            for key, val in row_dict.items():
                                key_upper = str(key).upper().strip()
                                # Skip technical clean column variables if any
                                if 'CLEAN' in key_upper:
                                    continue
                                info_lines.append(f"🔹 **{key}:** {clean_val(val)}")
                                
                            results.append("\n".join(info_lines))
                        break # Prevent reading duplicate rows for the same file sheet
                        
        except Exception:
            continue
            
    return list(set(results))

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # Remove any existing keyboard custom menus completely
    markup = telebot.types.ReplyKeyboardRemove(selective=False)
    bot.reply_to(
        message, 
        "Welcome to Smart KIPiA Search Bot!\n\nPlease enter the KIP TAG number to search across all databases (e.g., PT-1103, 21_TI_201, or LICA-10101):",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text.strip()
    
    if len(text) >= 3: 
        bot.send_message(message.chat.id, "🔍 Searching databases, please wait...")
        results = search_instrument_tag(text)
        
        if results:
            for result in results:
                bot.send_message(message.chat.id, result, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"❌ Match for `{text}` not found in any database. Please double-check the entry.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter at least 3 characters to search.")

bot.infinity_polling()
