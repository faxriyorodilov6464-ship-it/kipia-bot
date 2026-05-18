import os
import sys

# Serverda yoki telefonda papka yo'nalishini avtomatik to'g'rilash
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

# --- RENDER PORT BINDING XATOLIGINI TUZATISH QISMI ---
app = Flask('')

@app.route('/')
def home():
    return "KIPiA Bot is Running!"

def run_web_server():
    # Render taqdim etadigan PORT'ni oladi (odatda 10000 yoki o'zgaruvchan)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Veb-serverni alohida oqimda (Thread) fonda ishga tushiramiz
Thread(target=run_web_server).start()
# -----------------------------------------------------

# HTTP API Tokeningiz
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

def clean_val(val):
    """Bazadagi bo'shliqlar yoki tushunarsiz belgilarni chiroyli ko'rinishga keltirish"""
    if pd.isna(val) or str(val).strip() in ['-', '—', 'nan', 'N/A', 'NA', '_', '', 'nan/nan']:
        return "—"
    return str(val).strip()

def search_instrument_tag(search_query):
    search_query = str(search_query).strip().upper()
    clean_query = re.sub(r'[-_\s]', '', search_query)
    
    results = []
    
    # Yuklangan Excel fayllarni qidirish (.xlsx va .xls)
    files = glob.glob("*.xlsx") + glob.glob("*.xls")
    
    if not files:
        return ["⚠️ Serverda hech qanday Excel (.xlsx yoki .xls) fayli topilmadi!"]

    for file in files:
        try:
            file_upper = file.upper()
            file_name_short = os.path.basename(file)
            
            excel_file = pd.ExcelFile(file)
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)
                df.columns = df.columns.astype(str).str.strip()
                
                # --- INDORAMA DCS BAZALARI ---
                if "INDORAMA" in file_upper:
                    tag_col = None
                    for col in ['DCS TAG', 'DCS TAGS', 'FIELD TAG', '1617', 'DSC TAG']:
                        if col in df.columns:
                            tag_col = col
                            break
                    
                    if tag_col:
                        df['clean_tag_col'] = df[tag_col].astype(str).str.upper().str.replace(r'[-_\s]', '', regex=True)
                        matched_rows = df[df['clean_tag_col'].str.contains(clean_query, na=False)]
                        
                        for _, row in matched_rows.iterrows():
                            desc = row.get('DESCRIPTION', row.get('SERVICE', '—'))
                            sys_cab = row.get('SYSTEM CABINET', '—')
                            bar_cab = row.get('BARRIER CABINET', row.get('RELAY CABINET', '—'))
                            bar_name = row.get('BARRIER NAME', row.get('RELAY NAME', '—'))
                            ftb_cab = row.get('FTB CABINET', '—')
                            ftb_name = row.get('FTB NAME', '—')
                            ftb1 = row.get('FTB1', '—')
                            ftb2 = row.get('FTB2', '—')
                            
                            jb_name = row.get('IRP-TB NAME.', row.get('IRP TB NAME', row.get('IRP CABINET  FIELD', '—')))
                            jb_tb1 = row.get('TB (+)', row.get('IRP-TB (+)', '—'))
                            jb_tb2 = row.get('TB (-)', row.get('IRP TB (-)', '—'))
                            
                            msg = (
                                f"🌐 **TIZIM:** DCS ({sheet_name})\n"
                                f"📌 **TAG:** `{clean_val(row[tag_col])}`\n"
                                f"📝 **Tavsif:** {clean_val(desc)}\n"
                                f"🗄 **Cabinet:** System: {clean_val(sys_cab)} | Barrier: {clean_val(bar_cab)}\n"
                                f"🔌 **IOM / Channel:** No: {clean_val(row.get('IOM NO', '—'))} | Ch: {clean_val(row.get('CHANNEL NO', '—'))}\n"
                                f"⚡ **Baryer:** {clean_val(bar_name)} (In: {clean_val(row.get('TB1', '—'))}, Out: {clean_val(row.get('TB2', '—'))})\n"
                                f"🎛 **FTB (Kross):** Cab: {clean_val(ftb_cab)} | Name: {clean_val(ftb_name)} | Klema: {clean_val(ftb1)}, {clean_val(ftb2)}\n"
                                f"🗅 **Field (JB):** Name: {clean_val(jb_name)} | Klema: {clean_val(jb_tb1)}, {clean_val(jb_tb2)}\n"
                                f"📐 **Shkala:** {clean_val(row.get('RANGE LOW', '0'))} ~ {clean_val(row.get('RANGE HIGH', '—'))} {clean_val(row.get('ENG. UNIT', ''))}"
                            )
                            results.append(msg)
                
                # --- GDS VA PLC BAZALARI (302300 va 292300) ---
                elif "302300" in file_upper or "292300" in file_upper:
                    loop_col = None
                    for col in ['Loop Name', 'LOOP NAME', 'Tag', 'TAG']:
                        if col in df.columns:
                            loop_col = col
                            break
                    
                    if loop_col:
                        df['clean_loop_col'] = df[loop_col].astype(str).str.upper().str.replace(r'[-_\s]', '', regex=True)
                        matched_rows = df[df['clean_loop_col'].str.contains(clean_query, na=False)]
                        
                        for _, row in matched_rows.iterrows():
                            tizim_turi = "GDS" if "302300" in file_upper else "PLC"
                            
                            msg = (
                                f"🤖 **TIZIM:** {tizim_turi} ({sheet_name})\n"
                                f"📌 **TAG:** `{clean_val(row[loop_col])}`\n"
                                f"📝 **Asbob Nomi:** {clean_val(row.get('Instrument Name', row.get('Description', '—')))}\n"
                                f"📡 **Signal turi:** Kirish: {clean_val(row.get('Input Signal', '—'))} | Chiqish: {clean_val(row.get('Output Signal', '—'))}\n"
                                f"⚡ **Ta'minot (Power):** {clean_val(row.get('Input Power Supply', '—'))}\n"
                                f"💡 **Izoh / Rejim:** {clean_val(row.get('Remarks', '—'))}"
                            )
                            results.append(msg)

                # --- DATCHIKLAR BAZASI ---
                elif "DATCHIK" in file_upper:
                    for col in df.columns:
                        df['clean_col'] = df[col].astype(str).str.upper().str.replace(r'[-_\s]', '', regex=True)
                        if df['clean_col'].str.contains(clean_query, na=False).any():
                            matched_rows = df[df['clean_col'].str.contains(clean_query, na=False)]
                            for _, row in matched_rows.iterrows():
                                info_lines = [f"📊 **BAZA:** `{file_name_short}` ({sheet_name})"]
                                for c in df.columns:
                                    if c != 'clean_col' and str(row[c]).strip() != '':
                                        info_lines.append(f"🔹 **{c}:** {clean_val(row[c])}")
                                results.append("\n".join(info_lines))
                            break
                        
        except Exception:
            continue
            
    return list(set(results))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Assalomu alaykum Faxriyor! KIP TAG raqamini kiriting:")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text.strip()
    if len(text) >= 3: 
        bot.send_message(message.chat.id, "🔍 Bazadan qidirilmoqda...")
        natijalar = search_instrument_tag(text)
        if natijalar:
            for natija in natijalar:
                bot.send_message(message.chat.id, natija, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"❌ `{text}` topilmadi.")
    else:
        bot.send_message(message.chat.id, "⚠️ Kamida 3 ta belgi kiriting.")

bot.infinity_polling()
