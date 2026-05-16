import os
import telebot
from flask import Flask
from threading import Thread

# 1. RENDER UCHUN BEPUL VEB-SERVER QISMI
app = Flask('')

@app.route('/')
def home():
    return "Faxriyor Odilov tizimi muvaffaqiyatli ishlamoqda!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. TELEGRAM BOT QISMI
BOT_TOKEN = "8896826475:AAGiRygV79dpx-iOBnoS_W8RiOZ_H-inXuk"
bot = telebot.TeleBot(BOT_TOKEN)

# Boshlang'ich bosh menyu tugmalari
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = telebot.types.KeyboardButton("📊 mA ➡️ Foiz (%)")
    btn2 = telebot.types.KeyboardButton("📈 Foiz (%) ➡️ mA")
    btn3 = telebot.types.KeyboardButton("🌡️ Pt100 Qarshilik")
    btn4 = telebot.types.KeyboardButton("🛠️ KIPiA Nosozliklar")
    btn5 = telebot.types.KeyboardButton("📚 Muallif & Ma'lumot")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

# Ichki bo'limlardan ortga qaytish tugmasi
def back_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = telebot.types.KeyboardButton("🔙 Bosh menyuga qaytish")
    markup.add(btn)
    return markup

# /start buyrug'i kelganda yoki Ortga qaytilganda
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == "🔙 Bosh menyuga qaytish")
def send_welcome(message):
    welcome_text = (
        "🤖 **KIPiA va Avtomatika Tizimi Professional Boti**\n\n"
        "👨‍💻 Tizim yaratuvchisi: **Faxriyor Odilov**\n\n"
        "Kerakli muhandislik bo'limini tanlang:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# 1-bo'lim: mA dan foizni hisoblash
@bot.message_handler(func=lambda message: message.text == "📊 mA ➡️ Foiz (%)")
def ask_ma(message):
    msg = bot.send_message(
        message.chat.id, 
        "📥 Tok signalini kiriting (4 va 20 mA oralig'ida):\n*Masalan: 12 yoki 15.4*", 
        reply_markup=back_menu(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_ma_to_percent)

def calc_ma_to_percent(message):
    text = message.text.strip()
    if text == "🔙 Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        val = float(text.replace(',', '.'))
        if 4 <= val <= 20:
            pct = (val - 4) / 16 * 100
            bars = int(round(pct / 10))
            bar_str = "🟩" * bars + "⬜" * (10 - bars)
            res = f"📊 Kiritilgan: *{val} mA*\n📈 Natija: *{pct:.2f}%*\n💻 Shkala: [{bar_str}]"
            bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Xato! Faqat 4 va 20 mA oralig'ida kiriting:", reply_markup=back_menu())
            bot.register_next_step_handler(msg, calc_ma_to_percent)
    except ValueError:
        msg = bot.send_message(message.chat.id, "⚠️ Shunchaki raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_ma_to_percent)

# 2-bo'lim: Foizdan mA hisoblash
@bot.message_handler(func=lambda message: message.text == "📈 Foiz (%) ➡️ mA")
def ask_percent(message):
    msg = bot.send_message(
        message.chat.id, 
        "📥 Foiz qiymatini kiriting (0 va 100 oralig'ida):\n*Masalan: 50 yoki 82.5*", 
        reply_markup=back_menu(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_percent_to_ma)

def calc_percent_to_ma(message):
    text = message.text.strip()
    if text == "🔙 Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        val = float(text.replace(',', '.'))
        if 0 <= val <= 100:
            ma = (val / 100 * 16) + 4
            res = f"📈 Kiritilgan: *{val}%*\n📊 Kerakli signal: *{ma:.3f} mA*"
            bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Xato! Faqat 0 va 100 oralig'ida kiriting:", reply_markup=back_menu())
            bot.register_next_step_handler(msg, calc_percent_to_ma)
    except ValueError:
        msg = bot.send_message(message.chat.id, "⚠️ Shunchaki raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_percent_to_ma)

# 3-bo'lim: Pt100 Qarshilik hisoblash (RTD Standart)
@bot.message_handler(func=lambda message: message.text == "🌡️ Pt100 Qarshilik")
def ask_temp(message):
    msg = bot.send_message(
        message.chat.id, 
        "📥 Haroratni kiriting (°C):\n*Masalan: 0, 25 yoki 120*", 
        reply_markup=back_menu(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_pt100)

def calc_pt100(message):
    text = message.text.strip()
    if text == "🔙 Bosh menyuga qaytish":
        send_welcome(message)
        return
    try:
        t = float(text.replace(',', '.'))
        # Pt100 uchun standart Callendar-Van Dusen soddalashtirilgan formulasi (A=3.9083e-3)
        r = 100 * (1 + 0.0039083 * t)
        res = f"🌡️ Harorat: *{t} °C*\n🔌 Pt100 qarshiligi: *{r:.2f} Om (Ω)*"
        bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
    except ValueError:
        msg = bot.send_message(message.chat.id, "⚠️ Shunchaki raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_pt100)

# 4-bo'lim: KIPiA Nosozliklar
@bot.message_handler(func=lambda message: message.text == "🛠️ KIPiA Nosozliklar")
def troubleshooting(message):
    guide = (
        "🛠️ **KIPiA Tezkor Yo'riqnomasi (Troubleshooting):**\n\n"
        "🛑 **1. Signal 0 mA (Tok yo'q):**\n"
        "• Datchikka 24V DC kelayotganini tekshiring.\n"
        "• Tok zanjirida uzilish bor-yo'qligini tester bilan tekshiring.\n\n"
        "⚡ **2. Signal 24 mA dan yuqori (Overload):**\n"
        "• Datchik platasi qisqa tutashuv bo'lgan yoki datchik element darsligidan chiqqan (Parchalanish).\n"
        "• Tozalab qayta kalibrlash (Zero/Span) talab etiladi.\n\n"
        "📉 **3. Signal o'ynab turishi (Instability):**\n"
        "• Ekranlangan kabelni (Shield) erga (Ground) to'g'ri ulanganini tekshiring.\n"
        "• Signal liniyasi kuchli kuchlanish kabellari yonidan o'tmaganiga ishonch hosil qiling."
    )
    bot.send_message(message.chat.id, guide, reply_markup=back_menu(), parse_mode="Markdown")

# 5-bo'lim: Mualliflik va Ma'lumotnoma bo'limi
@bot.message_handler(func=lambda message: message.text == "📚 Muallif & Ma'lumot")
def info_author(message):
    info_text = (
        "🚀 **KIPiA Professional Yordamchi Tizimi**\n\n"
        "👨‍💻 **Dasturchi va Muallif:** Faxriyor Odilov\n"
        "⚙️ **Mutaxassislik:** Instrumentation & Industrial Automation Specialist\n"
        "📍 **Hudud:** Kokand\n\n"
        "📚 **Standart eslatmalar:**\n"
        "• 4 mA = 0%\n"
        "• 12 mA = 50%\n"
        "• 20 mA = 100%\n"
        "• Pt100 datchigi 0°C da aniq 100 Om berishi shart."
    )
    bot.send_message(message.chat.id, info_text, reply_markup=back_menu(), parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    print("Bot Faxriyor Odilov tomonidan muvaffaqiyatli yoqildi!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

