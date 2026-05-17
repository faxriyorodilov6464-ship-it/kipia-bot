import os
import math
import telebot
import pandas as pd
from flask import Flask
from threading import Thread

# 1. RENDER VEB-SERVER QISMI
app = Flask('')

@app.route('/')
def home():
    return "Faxriyor Odilov KIPiA Professional Bot Aktiv!"

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
            print(f"✅ Excel yuklandi: {len(datchiklar_baza)} ta datchik xotirada.")
        except Exception as e:
            print(f"❌ Excel xatosi: {e}")

load_excel_data()

# --- MENYULAR TIZIMI ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton("🔍 Datchik Qidirish (Excel)"))
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

# --- START VA QAYTISH MASALALARI ---
@bot.message_handler(commands=['start', 'stop'])
@bot.message_handler(func=lambda message: message.text == "Bosh menyuga qaytish")
def send_welcome(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    welcome_text = (
        "🤖 **Smart KIPiA Professional Bot v3.0**\n\n"
        "Hamma funksiyalar va kalkulyatorlar to'liq tekshirildi va faollashtirildi.\n"
        "Kerakli bo'limni pastdagi tugmalar orqali tanlang 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- 1. ALOHIDA KATAKCHA: EXCEL QIDIRUV REJIMI ---
@bot.message_handler(func=lambda message: message.text == "🔍 Datchik Qidirish (Excel)")
def excel_search_mode(message):
    msg = bot.send_message(
        message.chat.id, 
        "📝 **Datchik nomini (TAG) kiriting:**\n(Masalan: `21_TI_201` yoki `21_ZSC_302`)", 
        reply_markup=back_menu(), parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_excel_search)

def process_excel_search(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    
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
            f"📝 **Vazifasi:** {d['desc']}\n"
            f"🖥️ **Kros Panel / Cabinet:** `{d['cabinet']}`\n"
            f"📦 **JB / Marshalling:** `{d['jb']}`\n"
            f"🔌 **Ulanish klemalari:** `{d['terminals']}`"
        )
    else:
        response_text = f"⚠️ '{message.text}' datchigi Excel bazasidan topilmadi. Qayta tekshirib ko'ring."

    msg = bot.send_message(message.chat.id, response_text, reply_markup=back_menu(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_excel_search)

# --- 2. TOK SIGNALLARI KALKULYATORI ---
@bot.message_handler(func=lambda message: message.text == "Tok Signallari (mA / %)")
def tok_menu(message):
    msg = bot.send_message(
        message.chat.id, 
        "🔢 **mA yoki % qiymatni kiriting:**\n\n• 4-20 oralig'i -> Foizga (%)\n• 0-100 oralig'i -> Tokka (mA)", 
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
            res = "⚠️ Iltimos, 0-100 yoki 4-20 oralig'ida kiriting."
    except:
        res = "❌ Faqat to'g'ri raqam kiriting."
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_tok)

# --- 3. HARORAT KALKULYATORI ---
@bot.message_handler(func=lambda message: message.text == "Harorat (Pt, Termopara)")
def temp_menu(message):
    msg = bot.send_message(message.chat.id, "🌡️ **Pt100 qarshiligini (Om) kiriting:**\n(Masalan: `100` yoki `138.5`)", reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_temp)

def calc_temp(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        R = float(message.text.replace(',', '.'))
        A, B, R0 = 3.9083e-3, -5.775e-7, 100.0
        if R >= 100.0:
            t = (-A + math.sqrt(A**2 - 4*B*(1 - R/R0))) / (2*B)
        else:
            t = (R - 100.0) / 0.385
        res = f"🔌 **Qarshilik:** {R} Om\n🔥 **Harorat:** {t:.2f} °C"
    except:
        res = "❌ Xato qiymat. Faqat raqam yozing."
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_temp)

# --- 4. UNIVERSAL SHKALA (SCALING) ---
@bot.message_handler(func=lambda message: message.text == "Universal Shkala (Scaling)")
def scaling_menu(message):
    msg = bot.send_message(message.chat.id, "📐 **Format: `tok MinShkala MaksShkala`**\nMasalan: `12 0 160`", reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_scaling)

def calc_scaling(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        parts = message.text.replace(',', '.').split()
        current_ma, min_val, max_val = float(parts[0]), float(parts[1]), float(parts[2])
        if 4.0 <= current_ma <= 20.0:
            phys_val = min_val + ((current_ma - 4.0) / 16.0) * (max_val - min_val)
            res = f"📉 **Tok:** {current_ma} mA\n📊 **Shkala:** {min_val} ... {max_val}\n🎯 **Joriy Qiymat:** {phys_val:.2f}"
        else:
            res = "⚠️ Tok 4-20 mA oralig'ida bo'lsin!"
    except:
        res = "❌ Noto'g'ri format. Masalan: `12 0 160`"
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_scaling)

# --- 5. BOSIM VA SATH KALKULYATORI ---
@bot.message_handler(func=lambda message: message.text == "Bosim va Sath (Kalkulyator)")
def pressure_menu(message):
    msg = bot.send_message(
        message.chat.id, 
        "🛢️ **Gidrostatik sathni hisoblash**\nFormat: `Balandlik(m) Zichlik(kg/m³)`\nMasalan: `5 1000`", 
        reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, calc_pressure)

def calc_pressure(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        parts = message.text.replace(',', '.').split()
        h, rho = float(parts[0]), float(parts[1])
        g = 9.80665
        p_pa = rho * g * h
        p_bar = p_pa / 100000.0
        p_kpa = p_pa / 1000.0
        res = f"🛢️ **Sath:** {h} m | **Zichlik:** {rho} kg/m³\n⚡ **Bosim:** `{p_kpa:.2f} kPa` | `{p_bar:.4f} bar`"
    except:
        res = "❌ Format xato. Masalan: `5 1000` deb yozing."
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, calc_pressure)

# --- 6. FLOW TRANSMITTER KALKULYATORI ---
@bot.message_handler(func=lambda message: message.text == "Flow Transmitter (Oqim)")
def flow_menu(message):
    msg = bot.send_message(
        message.chat.id, 
        "🌊 **Diffbosim (dP) bo'yicha sarf (Root Extraction):**\nmA (4-20) yoki % (0-100) signalni kiriting:", 
        reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, calc_flow)

def calc_flow(message):
    if message.text == "Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        val = float(message.text.replace(',', '.'))
        if 4.0 <= val <= 20.0:
            pct_in = (val - 4.0) / 16.0
        elif 0.0 <= val <= 100.0:
            pct_in = val / 100.0
        else:
            pct_in = -1
            
        if 0 <= pct_in <= 1:
            flow_pct = math.sqrt(pct_in) * 100.0
            flow_ma = 4.0 + (math.sqrt(pct_in) * 16.0)
            res = f"📥 **Kirish dP signali:** {val}\n🎛️ **Haqiqiy Sarf (Flow):**\n• `{flow_pct:.2f} %` \n• `{flow_ma:.2f} mA`"
        else:
            res = "⚠️ Kiritilgan qiymat noto'g'ri oraliqda!"
    except:
        res = "❌ Faqat raqam yozing."
    msg = bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, calc_flow)

# --- 7. KIPiA METODIKA VA HART (KENGAYTIRILGAN TO'LIQ VARIANT) ---
@bot.message_handler(func=lambda message: message.text in ["KIPiA Metodika va HART", "Muallif"])
def info_buttons(message):
    if message.text == "Muallif":
        res = "👨‍💻 **Tizim bosh muallifi:** Faxriyor Odilov\n⚙️ **Sektor:** Instrumentation & Automation System (KIPiA)"
    else:
        res = (
            "📚 **PROFESSOR KIPiA QO'LLANMASI**\n\n"
            "📌 **1. MUHIM QISQARTMA SO'ZLAR (TERMINLAR):**\n"
            "• **DCS (AsuTP):** Distributed Control System — Markaziy boshqaruv tizimi (operator xonasi).\n"
            "• **ESD:** Emergency Shutdown System — Avariya holatida tizimni avtomat to'xtatish zanjiri.\n"
            "• **HART:** Highway Addressable Remote Transducer — Raqamli o'tish protokoli.\n"
            "• **PV:** Process Variable — Datchik o'lchayotgan joriy jismoniy qiymat (Bosim, harorat...).\n"
            "• **LRV / URV:** Lower/Upper Range Value — Shkalaning eng past (4mA) va eng baland (20mA) chegarasi.\n"
            "• **TAG:** Datchikning chizmadagi maxsus kodi (Masalan: `21_TI_201`).\n"
            "• **JB:** Junction Box — Sex ichidagi kabellar birlashadigan oraliq quti.\n\n"
            "🛠️ **2. HART-KOMMUNIKATOR SIRLARI:**\n"
            "• **Ulanish:** Kommunikator datchik klemalariga parallel ulanadi.\n"
            "• **Rezistor (250 Om):** Agar HART datchikni topa olmasa, zanjirga **250 Om** qarshilikni ketma-ket qo'shing. Bo'lmasa signal yutilib ketadi.\n"
            "• **Loop Test:** HART orqali operator xonasiga majburiy `4mA`, `12mA`, `20mA` yuborib zanjirni tekshirish mumkin.\n\n"
            "📐 **3. KALIBRLASH METODIKASI:**\n"
            "• **5 nuqta qoidasi:** Datchik `0% -> 25% -> 50% -> 75% -> 100%` nuqtalarda tekshiriladi.\n"
            "• **Xatolik (Pogreshnost):** Formula:\n"
            "  `γ = (Amaliy_Tok - Nazariy_Tok) / 16 * 100%`\n"
            "• **Multimetr:** Tok o'lchashda multimetr liniyaga har doim **ketma-ket (последовательно)** ulanishi shart!"
        )
    bot.send_message(message.chat.id, res, reply_markup=main_menu(), parse_mode="Markdown")

# --- NOTO'G'RI MATN YOZILSA TIZIM BUZILMASLIGI UCHUN ---
@bot.message_handler(func=lambda message: True)
def default_handle(message):
    bot.send_message(
        message.chat.id, 
        "⚠️ Iltimos, ma'lumot qidirish uchun avval yuqoridagi **'🔍 Datchik Qidirish (Excel)'** tugmasini bosing yoki kalkulyatorlardan birini tanlang.",
        reply_markup=main_menu()
    )

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
