import os
import telebot
from flask import Flask
from threading import Thread

# 1. RENDER UCHUN BEPUL VEB-SERVER QISMI (HIYLA)
app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run():
    # Render taqdim etadigan portni avtomatik o'qiydi, topolmasa 8080 qiladi
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. TELEGRAM BOT QISMI
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk" 
bot = telebot.TeleBot(BOT_TOKEN)

# Boshlang'ich menyu tugmalari
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("📊 Signal hisoblash")
    btn2 = telebot.types.KeyboardButton("📚 Ma'lumotnoma")
    markup.add(btn1, btn2)
    return markup

# /start buyrug'i kelganda
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Assalomu alaykum! KIPiA va Avtomatika tizimi botiga xush kelibsiz.\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# Ma'lumotnoma bo'limi
@bot.message_handler(func=lambda message: message.text == "📚 Ma'lumotnoma")
def info_message(message):
    info_text = (
        "⚙️ **Standart Tok Signallari (4-20 mA):**\n\n"
        "🔹 4 mA = 0%  (Boshlang'ich nuqta)\n"
        "🔹 12 mA = 50% (O'rta nuqta)\n"
        "🔹 20 mA = 100% (Maksimal nuqta)\n\n"
        "📍 Joylashuv: Kokand"
    )
    bot.send_message(message.chat.id, info_text, reply_markup=main_menu(), parse_mode="Markdown")

# Signal hisoblash bo'limi bosilganda
@bot.message_handler(func=lambda message: message.text == "📊 Signal hisoblash")
def ask_ma(message):
    msg = bot.send_message(message.chat.id, "Iltimos, mA qiymatini kiriting (masalan: 12 yoki 15.5):")
    bot.register_next_step_handler(msg, calculate_percentage)

# mA dan foizni hisoblash
def calculate_percentage(message):
    try:
        ma_value = float(message.text.replace(',', '.'))
        
        if 4 <= ma_value <= 20:
            # Formula: (mA - 4) / 16 * 100
            percentage = (ma_value - 4) / 16 * 100
            
            # Progress bar hosil qilish (10 ta katakcha)
            filled_bars = int(round(percentage / 10))
            bar_string = "🟩" * filled_bars + "⬜" * (10 - filled_bars)
            
            response = (
                f"📥 Kiritilgan signal: *{ma_value} mA*\n"
                f"📊 Natija: *{percentage:.2f}%*\n\n"
                f"Shkala: [{bar_string}]"
            )
        else:
            response = "⚠️ Xato! Tok signali faqat **4 mA va 20 mA** oralig'ida bo'lishi kerak."
            
    except ValueError:
        response = "❌ Iltimos, faqat raqam kiriting! (Masalan: 12 va hokazo)"

    bot.send_message(message.chat.id, response, reply_markup=main_menu(), parse_mode="Markdown")

# 3. LOYIHANI ISHGA TUSHIRISH
if __name__ == '__main__':
    # Render o'chirib qo'ymasligi uchun veb-serverni fonda yoqamiz
    keep_alive()
    
    print("Bot muvaffaqiyatli yoqildi va Render kutmoqda...")
    # Botni uzluksiz so'rovlar rejimida yoqish
    bot.infinity_polling()

