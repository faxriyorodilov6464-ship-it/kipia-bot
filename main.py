import os
import math
import telebot
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
        bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
    except:
        msg = bot.send_message(message.chat.id, "⚠️ To'g'ri raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, lambda m: calc_temperature(m, d_type))

# --- 3-BO'LIM: UNIVERSAL SCALING ---
@bot.message_handler(func=lambda message: message.text == "📐 Universal Shkala (Scaling)")
def ask_scale_setup(message):
    msg = bot.send_message(
        message.chat.id, 
        "📐 **Universal Shkala Kalkulyatori**\n\n"
        "Datchik diapazoni va joriy mA ni kiriting.\n"
        "Format: `Min_Shkala Max_Shkala Joriy_mA`\n"
        "*Misol:* `0 16 12`", 
        reply_markup=back_menu(), parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_universal_scaling)

def calc_universal_scaling(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        parts = message.text.strip().split()
        if len(parts) == 3:
            lrv = float(parts[0].replace(',', '.'))
            urv = float(parts[1].replace(',', '.'))
            ma = float(parts[2].replace(',', '.'))
            if 4 <= ma <= 20:
                result = lrv + ((ma - 4) / 16) * (urv - lrv)
                res = (
                    f"📐 **Scaling Natijasi:**\n\n"
                    f"🔹 Diapazon: *{lrv} - {urv}*\n"
                    f"🔹 O'lchangan signal: *{ma} mA*\n"
                    f"🟢 Liniyadagi Fizik Qiymat: **{result:.3f}**"
                )
                bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
            else:
                msg = bot.send_message(message.chat.id, "⚠️ mA qiymati 4 va 20 oralig'ida bo'lishi shart. Qayta kiriting:", reply_markup=back_menu())
                bot.register_next_step_handler(msg, calc_universal_scaling)
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Iltimos namunadagidek 3 ta raqam kiriting:", reply_markup=back_menu(), parse_mode="Markdown")
            bot.register_next_step_handler(msg, calc_universal_scaling)
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Ma'lumot xato kiritildi. Qayta urinib ko'ring:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_universal_scaling)

# --- 4-BO'LIM: BOSIM VA SATH ---
@bot.message_handler(func=lambda message: message.text == "💨 Bosim & Sath (Kalkulyator)")
def pressure_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➡️ Bosim Birliklari", "🌊 Gidrostatik Sath (kPa)", "🔙 Bosh menyuga qaytish")
    bot.send_message(message.chat.id, "💨 Kerakli xizmatni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "➡️ Bosim Birliklari")
def ask_press_conv(message):
    msg = bot.send_message(message.chat.id, "📥 Qiymatni `bar` hisobida kiriting (Masalan: `6`):", reply_markup=back_menu())
    bot.register_next_step_handler(msg, calc_pressure_conversion)

def calc_pressure_conversion(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        bar = float(message.text.strip().replace(',', '.'))
        kpa = bar * 100
        mpa = bar * 0.1
        kgf = bar * 1.01972
        psi = bar * 14.5038
        res = (
            f"💨 **{bar} bar** bosim konvertatsiyasi:\n\n"
            f"🔹 *{kpa:.2f}* kPa\n"
            f"🔹 *{mpa:.4f}* MPa\n"
            f"🔹 *{kgf:.3f}* kgf/cm²\n"
            f"🔹 *{psi:.2f}* PSI"
        )
        bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_pressure_conversion)

@bot.message_handler(func=lambda message: message.text == "🌊 Gidrostatik Sath (kPa)")
def ask_hydrostatic(message):
    msg = bot.send_message(
        message.chat.id, 
        "🌊 **Gidrostatik Sathni Hisoblash (P = ρ * g * h)**\n\n"
        "Suyuqlik balandligi (metrda) va zichligini (kg/m³) kiriting.\n"
        "Format: `Balandlik Zichlik`\n"
        "*Masalan:* `5 1000`", 
        reply_markup=back_menu(), parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_hydrostatic)

def calc_hydrostatic(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        parts = message.text.strip().split()
        h = float(parts[0].replace(',', '.'))
        rho = float(parts[1].replace(',', '.'))
        p_pa = rho * 9.80665 * h
        p_kpa = p_pa / 1000
        p_bar = p_kpa / 100
        res = (
            f"🌊 **Gidrostatik Hisob Kitob:**\n\n"
            f"🔹 Suyuqlik ustuni: *{h} m*\n"
            f"🔹 Zichlik: *{rho} kg/m³*\n\n"
            f"🟢 Datchik darsligidagi bosim:\n"
            f"⚡ **{p_kpa:.3f} kPa**\n"
            f"⚡ **{p_bar:.3f} bar**"
        )
        bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Format xato. Misoldagidek kiriting (`5 1000`):", reply_markup=back_menu(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, calc_hydrostatic)

# --- 5-BO'LIM: FLOW TRANSMITTER ---
@bot.message_handler(func=lambda message: message.text == "🌊 Flow Transmitter (Oqim)")
def flow_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🧮 DP Flow mA Calc", "📐 Square Root Extract", "🔙 Bosh menyuga qaytish")
    bot.send_message(message.chat.id, "🌊 Oqim (Flow) hisoblash bo'limini tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🧮 DP Flow mA Calc")
def ask_flow_ma(message):
    msg = bot.send_message(
        message.chat.id,
        "🧮 **DP Flow Transmitter chiqish tokini hisoblash**\n\n"
        "Maksimal oqim shkalasi (Qmax) va joriy oqim qiymatini (Q) kiriting.\n"
        "Format: `Max_Oqim Joriy_Oqim`\n"
        "*Masalan:* `200 100`",
        reply_markup=back_menu(), parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_flow_ma)

def calc_flow_ma(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        parts = message.text.strip().split()
        q_max = float(parts[0].replace(',', '.'))
        q_current = float(parts[1].replace(',', '.'))
        
        if q_current <= q_max and q_max > 0:
            ma = 4 + 16 * ((q_current / q_max) ** 2)
            res = (
                f"🌊 **Flow mA Natijasi:**\n\n"
                f"🔹 Max Diapazon: *{q_max}*\n"
                f"🔹 Joriy Oqim: *{q_current}*\n"
                f"⚡ Chiqish signali (DP datchik uchun): **{ma:.3f} mA**"
            )
            bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Joriy oqim maksimal shkaladan katta bo'lishi mumkin emas. Qayta kiriting:", reply_markup=back_menu())
            bot.register_next_step_handler(msg, calc_flow_ma)
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Ma'lumot noto'g'ri kiritildi. Namuna: `200 100`", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_flow_ma)

@bot.message_handler(func=lambda message: message.text == "📐 Square Root Extract")
def ask_sqrt_extract(message):
    msg = bot.send_message(
        message.chat.id,
        "📐 **Kvadrat Ildiz Shkalasini Tekshirish (Linear vs Square Root)**\n\n"
        "Datchikka berilgan kirish bosim foizini (0-100%) kiriting.\n"
        "*Masalan:* `25`",
        reply_markup=back_menu(), parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, calc_sqrt_extract)

def calc_sqrt_extract(message):
    if message.text == "🔙 Bosh menyuga qaytish": send_welcome(message); return
    try:
        input_percent = float(message.text.strip().replace(',', '.'))
        if 0 <= input_percent <= 100:
            output_percent = math.sqrt(input_percent / 100) * 100
            ma_linear = 4 + (input_percent / 100 * 16)
            ma_sqrt = 4 + (output_percent / 100 * 16)
            
            res = (
                f"📐 **Kvadrat Ildiz (Square Root Extraction):**\n\n"
                f"🔹 Kirish bosimi: *{input_percent}%* ({ma_linear:.2f} mA)\n"
                f"📈 Chiqish Oqimi: **{output_percent:.2f}%**\n"
                f"⚡ Chiqish Toki (Flow): **{ma_sqrt:.3f} mA**\n\n"
                f"*Metodika: Delta P datchiklarda 25% bosimda 50% oqim (12 mA) olinadi.*"
            )
            bot.send_message(message.chat.id, res, reply_markup=back_menu(), parse_mode="Markdown")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Faqat 0 va 100 oralig'ida foiz kiriting:", reply_markup=back_menu())
            bot.register_next_step_handler(msg, calc_sqrt_extract)
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Raqam kiriting:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, calc_sqrt_extract)

# --- 6-BO'LIM: KIPiA METODIKA & HART ---
@bot.message_handler(func=lambda message: message.text == "🛠️ KIPiA Metodika & HART")
def methodology_menu(message):
    text = (
        "🛠️ **KIPiA Muhandislik Qo'llanmasi:**\n\n"
        "ℹ️ **HART-Kommunikator Instruksiya:**\n"
        "1. **Online -> PV -> Diapazon sozlash:** Yangi datchik o'rnatilganda `LRV` (0%) va `URV` (100%) qiymatlarini zavod texnologik rejimiga moslang.\n"
        "2. **Zero Trim (Nollash):** Liniyada bosim mutlaqo yo'q bo'lganda datchik xatolik ko'rsatsa, HART orqali *Sensor Trim -> Zero Trim* bosing.\n"
        "3. **Polling Address:** Agar datchik DCS (AsuTP) tizimiga ko'p nuqtali (Multidrop) ulanayotgan bo'lsa, adresni 0 dan boshqa raqamga o'zgartiring.\n\n"
        "🛑 **Tezkor nosozlik bartaraf etish:**\n"
        "• **4 mA dan past signal:** Zanjirda qayerdadir qarshilik yuqori yoki datchik elementi shikastlangan.\n"
        "• **20.8 mA dan yuqori / 24 mA:** Tizim to'yingan (Overload) yoki datchik darsligida kuchli parchalanish / avariya yuz bergan."
    )
    bot.send_message(message.chat.id, text, reply_markup=back_menu(), parse_mode="Markdown")

# --- 7-BO'LIM: MUALLIF ---
@bot.message_handler(func=lambda message: message.text == "📚 Muallif")
def show_author(message):
    author_text = (
        "🚀 **KIPiA Professional Intelligent System**\n\n"
        "👨‍💻 **Dasturchi va G'oya Muallifi:** Faxriyor Odilov\n"
        "⚙️ **Yo'nalish:** Instrumentation, Metrology & Automation Specialist\n"
        "📍 **Hudud:** Kokand\n\n"
        "Tizim eng zamonaviy standartlar asosida avtomatika ustalari va muhandislarining og'irini yengil qilish uchun ishlab chiqildi."
    )
    bot.send_message(message.chat.id, author_text, reply_markup=back_menu(), parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
