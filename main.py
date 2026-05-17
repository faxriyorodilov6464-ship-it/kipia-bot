import os
import math
import telebot
import pandas as pd
from flask import Flask
from threading import Thread

# 1. RENDER SERVER UCHUN PORT
app = Flask('')

@app.route('/')
def home():
    return "Faxriyor Odilov KIPiA Bot Aktiv!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. TELEGRAM BOT SOZLAMASI
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

EXCEL_FILE = "datchiklar.xlsx"
datchiklar_baza = {}

# 3. EXCELNI TO'LIQ (CHAP VA O'NG TOMONLARINI) O'QISH ALGORITMI
def load_excel_data():
    global datchiklar_baza
    if os.path.exists(EXCEL_FILE):
        try:
            excel_sheets = pd.read_excel(EXCEL_FILE, sheet_name=None, header=None)
            datchiklar_baza.clear()
            
            for sheet_name, df in excel_sheets.items():
                if df.empty:
                    continue
                
                # Sarlavha qatorini (0-qator) tozalab olamiz
                header_row = [str(c).strip().upper() for c in df.iloc[0]]
                
                # Jadval ichida "DCS TAG" deb yozilgan barcha ustunlarning joyini (indeksini) topamiz
                tag_ustunlari = []
                for idx, col_name in enumerate(header_row):
                    if "DCS TAG" in col_name or "FIELD TAG" in col_name:
                        tag_ustunlari.append(idx)
                
                # Agar ushbu varoqda datchik ustuni topilsa, qatorlarni o'qiymiz
                if tag_ustunlari:
                    for row_idx in range(1, len(df)):
                        row = df.iloc[row_idx]
                        
                        for t_idx in tag_ustunlari:
                            if t_idx < len(row) and pd.notna(row[t_idx]):
                                tag_val = str(row[t_idx]).strip().upper().replace(' ', '_')
                                
                                # Zaxira qatorlar bo'lsa tashlab ketamiz
                                if not tag_val or tag_val == 'NAN' or tag_val.startswith('SPARE'):
                                    continue
                                
                                # Datchik atrofidagi ma'lumotlarni ustun tartibiga qarab olamiz
                                desc_val = str(row[t_idx+1]).strip() if t_idx+1 < len(row) and pd.notna(row[t_idx+1]) else "Ma'lumot yo'q"
                                cab_val = str(row[t_idx+2]).strip() if t_idx+2 < len(row) and pd.notna(row[t_idx+2]) else "Ma'lumot yo'q"
                                jb_val = str(row[t_idx+3]).strip() if t_idx+3 < len(row) and pd.notna(row[t_idx+3]) else "Ma'lumot yo'q"
                                
                                t1 = str(row[t_idx+4]).strip() if t_idx+4 < len(row) and pd.notna(row[t_idx+4]) else "-"
                                t2 = str(row[t_idx+5]).strip() if t_idx+5 < len(row) and pd.notna(row[t_idx+5]) else "-"
                                terminals_val = f"{t1} / {t2}" if t1 != 'nan' and t2 != 'nan' else "-"
                                
                                # Bazaga qo'shamiz
                                datchiklar_baza[tag_val] = {
                                    "sheet": sheet_name,
                                    "desc": desc_val,
                                    "cabinet": cab_val,
                                    "jb": jb_val,
                                    "terminals": terminals_val
                                }
            print(f"✅ Baza tayyor! Jami {len(datchiklar_baza)} ta datchik xotiraga olindi.")
        except Exception as e:
            print(f"❌ Excel o'qishda xato: {e}")
    else:
        print("⚠️ 'datchiklar.xlsx' fayli topilmadi!")

load_excel_data()

# --- MENYULAR ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton("Tok Signallari (mA / %)"),
        telebot.types.KeyboardButton("Harorat (Pt, Termopara)"),
        telebot.types.KeyboardButton("Universal Shkala (Scaling)"),
        telebot.types.KeyboardButton("Bosim va Sath (Kalkulyator)"),
        telebot.types.KeyboardButton("Flow Transmitter (Oqim)"),
        telebot.types.KeyboardButton("KIPiA Metodika va HART"),
        telebot.types.KeyboardButton("Muallif")
    )
    return markup

@bot.message_handler(commands=['start', 'stop'])
@bot.message_handler(func=lambda message: message.text == "Bosh menyuga qaytish")
def send_welcome(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    welcome_text = (
        "🤖 **Smart KIPiA Bot**\n\n"
        "Excel faylingizdagi barcha datchiklar (chap va o'ng ustunlar) bazaga yuklandi.\n"
        "🔍 **Datchikni qidirish uchun** uning nomini yozib yuboring (Masalan: `21_TI_201`):"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- SMART QIDIRUV (HAMMA USTUNLARNI SOLISHTIRISH) ---
@bot.message_handler(func=lambda message: True)
def search_tag(message):
    user_text = message.text.strip().upper().replace(' ', '_')
    
    # To'g'ridan-to'g'ri qidirish yoki qisman o'xshashlikni tekshirish
    found_tag = None
    if user_text in datchiklar_baza:
        found_tag = user_text
    else:
        # Agar foydalanuvchi chiziqchalarsiz yozsa ham tekshiramiz
        for k in datchiklar_baza.keys():
            if user_text in k or user_text.replace('_', '') in k.replace('_', ''):
                found_tag = k
                break

    if found_tag:
        d = datchiklar_baza[found_tag]
        response_text = (
            f"🔍 **Datchik topildi: {found_tag}**\n"
            f"📁 **Varaq (Sheet):** {d['sheet']}\n\n"
            f"📝 **Vazifasi (Description):** {d['desc']}\n"
            f"🖥️ **Kros Panel / Cabinet:** `{d['cabinet']}`\n"
            f"📦 **JB / Marshalling:** `{d['jb']}`\n"
            f"🔌 **Ulanish klemalari:** `{d['terminals']}`"
        )
        bot.send_message(message.chat.id, response_text, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.send_message(
            message.chat.id, 
            f"⚠️ '{message.text}' datchigi yuklangan Excel fayli ichidan topilmadi.\nIltimos, nomini tekshirib qaytadan yozing.",
            reply_markup=main_menu()
        )

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
