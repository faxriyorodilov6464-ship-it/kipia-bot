import os
import math
import telebot
import pandas as pd
from flask import Flask
from threading import Thread

# 1. RENDER VEB-SERVER KISMI
app = Flask('')

@app.route('/')
def home():
    return "Faxriyor Odilov Smart KIPiA Tizimi Aktiv!"

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

# 3. EXCELNI TO'LIQ O'QISH FUNKSIYASI
def load_excel_data():
    global datchiklar_baza
    if os.path.exists(EXCEL_FILE):
        try:
            excel_sheets = pd.read_excel(EXCEL_FILE, sheet_name=None, header=None)
            datchiklar_baza.clear()
            
            for sheet_name, df in excel_sheets.items():
                if df.empty:
                    continue
                
                header_row = [str(c).strip().upper() for c in df.iloc[0]]
                tag_ustunlari = []
                for idx, col_name in enumerate(header_row):
                    if "DCS TAG" in col_name or "FIELD TAG" in col_name:
                        tag_ustunlari.append(idx)
                
                if tag_ustunlari:
                    for row_idx in range(1, len(df)):
                        row = df.iloc[row_idx]
                        for t_idx in tag_ustunlari:
                            if t_idx < len(row) and pd.notna(row[t_idx]):
                                tag_val = str(row[t_idx]).strip().upper().replace(' ', '_')
                                if not tag_val or tag_val == 'NAN' or tag_val.startswith('SPARE'):
                                    continue
                                
                                desc_val = str(row[t_idx+1]).strip() if t_idx+1 < len(row) and pd.notna(row[t_idx+1]) else "Ma'lumot yo'q"
                                cab_val = str(row[t_idx+2]).strip() if t_idx+2 < len(row) and pd.notna(row[t_idx+2]) else "Ma'lumot yo'q"
                                jb_val = str(row[t_idx+3]).strip() if t_idx+3 < len(row) and pd.notna(row[t_idx+3]) else "Ma'lumot yo'q"
                                
                                t1 = str(row[t_idx+4]).strip() if t_idx+4 < len(row) and pd.notna(row[t_idx+4]) else "-"
                                t2 = str(row[t_idx+5]).strip() if t_idx+5 < len(row) and pd.notna(row[t_idx+5]) else "-"
                                terminals_val = f"{t1} / {t2}" if t1 != 'nan' and t2 != 'nan' else "-"
                                
                                datchiklar_baza[tag_val] = {
                                    "sheet": sheet_name,
                                    "desc": desc_val,
                                    "cabinet": cab_val,
                                    "jb": jb_val,
                                    "terminals": terminals_val
                                }
            print(f"✅ Excel yuklandi: {len(datchiklar_baza)} ta datchik.")
        except Exception as e:
            print(f"❌ Excel xatosi: {e}")

load_excel_data()

# --- MENYULAR TIZIMI ---
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

def back_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Bosh menyuga qaytish"))
    return markup

# --- START KOMANDASI ---
@bot.message_handler(commands=['start', 'stop'])
@bot.message_handler(func=lambda message: message.text == "Bosh menyuga qaytish")
def send_welcome(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    welcome_text = (
        "🤖 **Smart KIPiA Tizimiga xush kelibsiz!**\n\n"
        "Excel bazasi va kalkulyatorlar to'liq faol holatda.\n\n"
        "🔍 **Datchik qidirish uchun:** Ixtiyoriy DCS TAG nomini yozib yuboring.\n"
        "🧮 **Hisob-kitoblar uchun:** Pastdagi tugmalardan foydalaning."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- 1. TOK SIGNALLARI KALKULYATORI (mA / %) ---
@bot.message_handler(func=lambda message: message.text == "Tok Signallari (mA / %)")
def tok_menu(message):
    msg = bot.send_message(
        message.chat.id, 
        "🔢 **mA yoki % qiymatni kiriting:**\n\n"
        "• Agar `4` dan `20` gacha raqam kiritsangiz — foizga (%) o'tkazadi.\n"
        "• Agar `0` dan `100` gacha raqam kiritsangiz — tokka (mA) o'tkazadi.", 
        reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, calc_tok)

def calc_tok(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        val = float(message.text.replace(',', '.'))
        if 4.0 <= val <= 20.0:
            pers = (val - 4.0) / 16.0 * 100.0
            res = f"📊 **Kiritildi:** {val} mA\n🎯 **Natija:** {pers:.2f} %"
        elif 0.0 <= val <= 100.0:
            ma = 4.0 + (val / 100.0 * 16.0)
            res = f"📊 **Kiritildi:** {val} %\n🎯 **Natija:** {ma:.2f} mA"
        else:
            res = "⚠️ Iltimos, 0-100 (%) yoki 4-20 (mA) oralig'ida qiymat kiriting."
    except:
        res = "❌ Xato raqam kiritildi. Qaytadan urinib ko'ring."
    
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_tok)

# --- 2. HARORAT KALKULYATORI (Pt100 / Pt1000) ---
@bot.message_handler(func=lambda message: message.text == "Harorat (Pt, Termopara)")
def temp_menu(message):
    msg = bot.send_message(
        message.chat.id, 
        "🌡️ **Pt100 uchun qarshilik (Om) qiymatini kiriting:**\n(Masalan: `100` yoki `138.5`)", 
        reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, calc_temp)

def calc_temp(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        R = float(message.text.replace(',', '.'))
        A = 3.9083e-3
        B = -5.775e-7
        R0 = 100.0
        
        if R >= 100.0:
            t = (-A + math.sqrt(A**2 - 4*B*(1 - R/R0))) / (2*B)
            res = f"🔌 **Qarshilik:** {R} Om\n🔥 **Harorat:** {t:.2f} °C (Pt100)"
        else:
            t = (R - 100.0) / 0.385
            res = f"🔌 **Qarshilik:** {R} Om\n❄️ **Harorat:** {t:.2f} °C (Pt100)"
    except:
        res = "❌ Xato qiymat kiritildi. Faqat raqam yozing."
        
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_temp)

# --- 3. UNIVERSAL SHKALA (SCALING) ---
@bot.message_handler(func=lambda message: message.text == "Universal Shkala (Scaling)")
def scaling_menu(message):
    msg = bot.send_message(
        message.chat.id, 
        "📐 **Scaling hisoblash uchun ma'lumotlarni mana bu ko'rinishda yuboring:**\n\n"
        "`tok MinShkala MaksShkala`\n\n"
        "**Masalan (12mA, shkala 0-160):**\n`12 0 160`", 
        parse_mode="Markdown", reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, calc_scaling)

def calc_scaling(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        parts = message.text.replace(',', '.').split()
        current_ma = float(parts[0])
        min_val = float(parts[1])
        max_val = float(parts[2])
        
        if 4.0 <= current_ma <= 20.0:
            phys_val = min_val + ((current_ma - 4.0) / 16.0) * (max_val - min_val)
            res = f"📉 **Tok:** {current_ma} mA\n📊 **Shkala:** {min_val} ... {max_val}\n🎯 **Joriy Qiymat:** {phys_val:.2f}"
        else:
            res = "⚠️ Tok signali 4 mA va 20 mA oralig'ida bo'lishi kerak!"
    except:
        res = "❌ Format noto'g'ri. Masalan shunday yozing: `12 0 160`"
        
    msg = bot.send_message(message.chat.id, res, parse_mode="Markdown", reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_scaling)

# --- FAQAT AXBOROT TUGLAMARI ---
@bot.message_handler(func=lambda message: message.text in ["Bosim va Sath (Kalkulyator)", "Flow Transmitter (Oqim)", "KIPiA Metodika va HART", "Muallif"])
def info_buttons(message):
    if message.text == "Muallif":
        res = "👨‍💻 **Tizim bosh muallifi:** Faxriyor Odilov\n⚙️ **Sektor:** Instrumentation & Automation System (KIPiA)"
    else:
        res = f"ℹ️ **{message.text}** bo'limi hozircha loyihalash jarayonida. Tez orada ushbu kalkulyator ham ishga tushadi!"
    bot.send_message(message.chat.id, res, reply_markup=main_menu())

# --- EXCEL DAN DATCHIK QIDIRISH (MATNLI XABARLAR UCHUN) ---
@bot.message_handler(func=lambda message: True)
def search_tag(message):
    user_text = message.text.strip().upper().replace(' ', '_')
    found_tag = None
    
    if user_text in datchiklar_baza:
        found_tag = user_text
    else:
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
            f"⚠️ '{message.text}' datchigi Excel bazasidan ham, kalkulyator buyruqlaridan ham topilmadi. Qayta tekshiring.",
            reply_markup=main_menu()
        )

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
