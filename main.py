import os
import telebot
import math
from flask import Flask
from threading import Thread

# 1. RENDER UCHUN VEB-SERVER QISMI
app = Flask('')

@app.route('/')
def home():
    return "Faxriyor Odilov KIPiA Ensiklopediyasi Tizimi Aktiv!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. TELEGRAM BOT QISMI
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

# --- MENYULAR ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton("📊 Tok Signallari (mA / %)"),
        telebot.types.KeyboardButton("🌡️ Harorat (Pt, Termopara)"),
        telebot.types.KeyboardButton("📐 Universal Shkala (Scaling)"),
        telebot.types.KeyboardButton("💨 Bosim & Sath (Kalkulyator)"),
        telebot.types.KeyboardButton("🌊 Flow Transmitter (Oqim)"),
        telebot.types.KeyboardButton("🛠️ KIPiA Metodika & HART"),
        telebot.types.KeyboardButton("📚 Muallif")
    )
    return markup

def back_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("🔙 Bosh menyuga qaytish"))
    return markup

# --- START VA ORTGA QAYTISH ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == "🔙 Bosh menyuga qaytish")
def send_welcome(message):
    welcome_text = (
        "🤖 **KIPiA Professional Muhandislik Ensiklopediyasi**\n\n"
        "👨‍💻 Tizim bosh muallifi: **Faxriyor Odilov**\n"
        "⚙️ Sektor: Instrumentation & Automation System\n\n"
        "O'lchov asboblari va hisob-kitoblar bo'limini tanlang:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- 1-BO'LIM: TOK SIGNALLARI ---
@bot.message_handler(func=lambda message: message.text == "📊 Tok Signallari (mA / %)")
def tok_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➡️ mA dan Foizga (%)", "➡️ Foizdan (%) mA ga", "🔙 Bosh menyuga qaytish")
    bot.send_message(message.chat.id, "📊 Tok signali yo'nalishini tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "➡️ mA dan Foizga (%)")
def ask_ma(message):
    msg = bot.send_message(message.chat.id, "📥 Tok signalini kiriting (4-20 mA):\n*Masalan: 12 yoki 16.5*", reply_markup=back_menu(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, calc_ma_to_pc)

def calc_ma_to_pc(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        val = float(message.text.strip().replace(',', '.'))
        if 4 <= val <= 20:
            pct = (val - 4) / 16 * 100
            bars = int(round(pct / 10))
            bar_str = "🟩" * bars + "⬜" * (10 - bars)
            bot.send_message(message.chat.id, f"📊 Signal: *{val} mA*\n📈 Natija: *{pct:.2f}%*\n💻 Shkala: [{bar_str}]", reply_markup=back_menu(), parse_mode="Markdown")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Faqat 4 va 20 mA oralig'ida kiriting:", reply_markup=back_menu())
            bot.register_next_step_handler(msg, calc_ma_to_pc)
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_ma_to_pc)

@bot.message_handler(func=lambda message: message.text == "➡️ Foizdan (%) mA ga")
def ask_pc(message):
    msg = bot.send_message(message.chat.id, "📥 Foizni kiriting (0-100%):\n*Masalan: 50 yoki 75*", reply_markup=back_menu(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, calc_pc_to_ma)

def calc_pc_to_ma(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        val = float(message.text.strip().replace(',', '.'))
        if 0 <= val <= 100:
            ma = (val / 100 * 16) + 4
            bot.send_message(message.chat.id, f"📈 Kiritilgan: *{val}%*\n📊 Tok signali: *{ma:.3f} mA*", reply_markup=back_menu(), parse_mode="Markdown")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Faqat 0 va 100 oralig'ida kiriting:", reply_markup=back_menu())
            bot.register_next_step_handler(msg, calc_pc_to_ma)
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_pc_to_ma)

# --- 2-BO'LIM: HARORAT ---
@bot.message_handler(func=lambda message: message.text == "🌡️ Harorat (Pt, Termopara)")
def temp_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🌡️ Pt100 Om", "🌡️ Pt1000 Om", "🔥 K-Turi Termopara (mV)", "🔙 Bosh menyuga qaytish")
    bot.send_message(message.chat.id, "🌡️ Datchik turini tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["🌡️ Pt100 Om", "🌡️ Pt1000 Om", "🔥 K-Turi Termopara (mV)"])
def ask_temp_val(message):
    d_type = message.text
    msg = bot.send_message(message.chat.id, f"📥 Harorat qiymatini kiriting (°C):\n*Masalan: 25 yoki 150*", reply_markup=back_menu(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: calc_temperature(m, d_type))

def calc_temperature(message, d_type):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        t = float(message.text.strip().replace(',', '.'))
        if d_type == "🌡️ Pt100 Om":
            r = 100 * (1 + 0.0039083 * t)
            res = f"🌡️ Pt100 datchigi\n🟢 Harorat: *{t} °C*\n🔌 Qarshilik: *{r:.2f} Om (Ω)*"
        elif d_type == "🌡️ Pt1000 Om":
            r = 1000 * (1 + 0.0039083 * t)
            res = f"🌡️ Pt1000 datchigi\n🟢 Harorat: *{t} °C*\n🔌 Qarshilik: *{r:.2f} Om (Ω)*"
        else:
            mv = t * 0.0412
            res = f"🔥 K-Type Termopara\n🟢 Harorat: *{t} °C*\n⚡ Chiqish signali: *{mv:.3f} mV*"
        bot.send_message(
