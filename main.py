import os
import re
import threading
import pandas as pd
from telebot import TeleBot, types
from flask import Flask

# ==========================================
# 1. FLASK VEB-SERVER (Render o'chib qolmasligi uchun)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Smart KPIA Bot is live and running flawlessly!"

# ==========================================
# 2. BOT VA BAZA SOZLAMALARI
# ==========================================
TOKEN = "8896826475:AAE_Z0W7Rhm6ynHH2a0smKjTyvXjW9GlLFM"
bot = TeleBot(TOKEN)

EXCEL_FILE = "Indorama IO legend.xlsx"
db_datchiklar = {}

def load_excel_data():
    """Excel faylidagi barcha sahifalarni aqlli skanerlash funksiyasi"""
    global db_datchiklar
    db_datchiklar.clear()
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Xatolik: '{EXCEL_FILE}' fayli loyiha ichida topilmadi!")
        return

    try:
        xls = pd.ExcelFile(EXCEL_FILE)
        for sheet_name in xls.sheet_names:
            # Har bir sahifani o'qiymiz
            df = xls.parse(sheet_name)
            
            # Ustun nomlarini tozalab, hammasini KATTA harfga o'tkazamiz
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Tag yozilgan ustunni qidirish (Sizning faylingizdagi variantlar)
            tag_col = None
            for candidate in ['FIELD TAG', 'DCS TAG', 'TAG FOR IO CARD', 'DCS TAGS', 'DSC TAG']:
                if candidate in df.columns:
                    tag_col = candidate
                    break
            
            if not tag_col:
                continue  # Agar bu sahifada datchik taglari bo'lmasa, keyingisiga o'tamiz

            # Kerakli diapazon va birlik ustunlarini aniqlash
            min_col = next((c for c in df.columns if 'RANGE  LOW' in c or 'RANGE LOW' in c), None)
            max_col = next((c for c in df.columns if 'RANGE HIGH' in c or 'RANGE HIGH' in c or 'CALIBRATION HIGH' in c), None)
            unit_col = next((c for c in df.columns if 'ENG. UNIT' in c or 'ENGG. UNIT' in c or 'ENG.UNIT' in c or 'UNIT' in c), None)
            desc_col = next((c for c in df.columns if 'DESCRIPTION' in c or 'SERVICE' in c), None)

            for _, row in df.iterrows():
                tag_val = str(row[tag_col]).strip()
                
                # Bo'sh yoki keraksiz qatorlarni tashlab ketamiz
                if not tag_val or tag_val.lower() in ['nan', 'none', '', 'spare', '-', '_']:
                    continue
                
                # Qidiruv oson bo'lishi uchun belgilarni tozalaymiz (Masalan: 21-PT-1108A -> 21PT1108A)
                clean_tag = re.sub(r'[^A-Z0-9]', '', tag_val.upper())
                
                # Diapazon qiymatlarini xavfsiz o'qish (Raqam bo'lsa o'qiydi, bo'lmasa None)
                min_val, max_val = None, None
                if min_col:
                    try: min_val = float(str(row[min_col]).replace(",", "."))
                    except: pass
                if max_col:
                    try: max_val = float(str(row[max_col]).replace(",", "."))
                    except: pass
                
                unit_val = str(row[unit_col]).strip() if unit_col and pd.notna(row[unit_col]) else ""
                if unit_val.lower() in ['nan', '-', 'na']: unit_val = ""
                
                desc_val = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else "Kiritilmagan"
                if desc_val.lower() in ['nan', 'spare']: desc_val = "Kiritilmagan"

                # Qo'shimcha foydali ma'lumotlarni yig'ish (IOM TYPE, MODULE NOS, CHANNEL NO)
                extra_info = []
                for extra_c in ['IOM TYPE', 'MODULE NOS', 'CHANNEL NO', 'IO TB']:
                    if extra_c in df.columns and pd.notna(row[extra_c]):
                        extra_info.append(f"<b>{extra_c}:</b> {row[extra_c]}")

                db_datchiklar[clean_tag] = {
                    "original_tag": tag_val,
                    "sheet": sheet_name,
                    "description": desc_val,
                    "min": min_val,
                    "max": max_val,
                    "unit": unit_val,
                    "extra": "\n".join(extra_info)
                }
        print(f"🚀 Baza muvaffaqiyatli yuklandi! Jami datchiklar soni: {len(db_datchiklar)}")
    except Exception as e:
        print(f"❌ Excel o'qishda xatolik yuz berdi: {e}")

# Kod ishga tushganda bazani yuklaymiz
load_excel_data()
user_states = {}

# ==========================================
# 3. TELEGRAM BOT FUNKSIYALARI
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 <b>Salom Faxriyor! Smart KPIA Botiga xush kelibsiz!</b>\n\n"
        "🔍 Datchik haqida ma'lumot olish uchun uning <b>Tag raqamini</b> yozing.\n"
        "<i>Masalan: 21-PT-1108A yoki 270PDT20</i>\n\n"
        "🔄 Excel bazasini qayta yangilash uchun: /refresh"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['refresh'])
def refresh_database(message):
    load_excel_data()
    bot.reply_to(message, f"🔄 Excel bazasi qayta skner qilindi!\n🎯 Jami faol datchiklar: <b>{len(db_datchiklar)} ta</b>", parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # Agar foydalanuvchi hisoblash rejimida bo'lsa
    if chat_id in user_states:
        state = user_states[chat_id]
        mode = state["mode"]
        tag_key = state["tag"]
        datchik = db_datchiklar[tag_key]
        
        if text.lower() in ['ortga', 'back', 'cancel', 'bekor qilish']:
            del user_states[chat_id]
            bot.send_message(chat_id, "⚙️ Qidiruv rejimiga qaytdingiz. Yangi Tag kiritishingiz mumkin.")
            return

        try:
            val = float(text.replace(",", "."))
            Min = datchik["min"]
            Max = datchik["max"]
            Unit = datchik["unit"]

            if mode == "ma_to_val":
                if not (4 <= val <= 20):
                    bot.send_message(chat_id, "⚠️ Oqim qiymati 4 va 20 mA orasida bo'lishi kerak! Qaytadan kiriting:")
                    return
                natija = ((val - 4) / 16) * (Max - Min) + Min
                javob = f"📊 <b>Hisob natijasi ({datchik['original_tag']}):</b>\n\n🔌 Kiritilgan oqim: <code>{val} mA</code>\n📈 Hisoblangan qiymat: <b>{natija:.3f} {Unit}</b>"
                
            elif mode == "val_to_ma":
                if val < Min or val > Max:
                    bot.send_message(chat_id, f"⚠️ Qiymat diapazon ichida bo'lishi kerak ({Min} - {Max})! Qaytadan kiriting:")
                    return
                if Max - Min == 0: nilai_ma = 4.0
                else: nilai_ma = ((val - Min) / (Max - Min)) * 16 + 4
                javob = f"📊 <b>Hisob natijasi ({datchik['original_tag']}):</b>\n\n📈 Kiritilgan qiymat: <code>{val} {Unit}</code>\n🔌 Kerakli oqim: <b>{nilai_ma:.3f} mA</b>"

            bot.send_message(chat_id, javob, parse_mode="HTML")
            del user_states[chat_id]
            
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("🔄 Qayta hisoblash", callback_data=f"calc_{mode}_{tag_key}"),
                types.InlineKeyboardButton("🔍 Yangi qidiruv", callback_data="new_search")
            )
            bot.send_message(chat_id, "Yana hisoblaymizmi?", reply_markup=markup)
        except ValueError:
            bot.send_message(chat_id, "❌ Iltimos, faqat to'g'ri raqam kiriting:")
        return

    # Oddiy qidiruv rejimi
    clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())

    if clean_text in db_datchiklar:
        datchik = db_datchiklar[clean_text]
        javob = (
            f"📋 <b>Datchik topildi!</b>\n\n"
            f"🏷 <b>Tag:</b> <code>{datchik['original_tag']}</code>\n"
            f"🗂 <b>Sahifa (Sheet):</b> {datchik['sheet']}\n"
            f"📝 <b>Tavsif (Service):</b> {datchik['description']}\n"
        )
        
        # Agar analog datchik bo'lsa (diapazoni bor bo'lsa)
        if datchik["min"] is not None and datchik["max"] is not None:
            javob += f"🔢 <b>Diapazon:</b> {datchik['min']} — {datchik['max']} {datchik['unit']}\n"
        else:
            javob += f"🔢 <b>Diapazon:</b> Diskret datchik (Diapazon mavjud emas)\n"
            
        if datchik["extra"]:
            javob += f"\n⚙️ <b>Texnik modullar:</b>\n{datchik['extra']}"

        markup = types.InlineKeyboardMarkup()
        if datchik["min"] is not None and datchik["max"] is not None:
            btn1 = types.InlineKeyboardButton("🔌 mA ➡️ Qiymat", callback_data=f"calc_ma_to_val_{clean_text}")
            btn2 = types.InlineKeyboardButton("📈 Qiymat ➡️ mA", callback_data=f"calc_val_to_ma_{clean_text}")
            markup.row(btn1, btn2)
        else:
            markup.row(types.InlineKeyboardButton("🔍 Yangi qidiruv", callback_data="new_search"))
        
        bot.send_message(chat_id, javob, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"❌ Kechirasiz Faxriyor, bazadan <b>{text}</b> nomli datchik topilmadi.", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "new_search":
        if chat_id in user_states: del user_states[chat_id]
        bot.send_message(chat_id, "🔍 Datchik Tag raqamini kiriting:")
        bot.answer_callback_query(call.id)
        return

    if data.startswith("calc_"):
        if "ma_to_val" in data:
            mode = "ma_to_val"
            tag_key = data.replace("calc_ma_to_val_", "")
        else:
            mode = "val_to_ma"
            tag_key = data.replace("calc_val_to_ma_", "")

        if tag_key in db_datchiklar:
            datchik = db_datchiklar[tag_key]
            user_states[chat_id] = {"mode": mode, "tag": tag_key}
            
            if mode == "ma_to_val":
                msg = f"🔌 <b>[mA ➡️ Qiymat]</b>\n\n<code>{datchik['original_tag']}</code> uchun oqim qiymatini yuboring (4 - 20 mA oralig'ida):"
            else:
                msg = f"📈 <b>[Qiymat ➡️ mA]</b>\n\n<code>{datchik['original_tag']}</code> uchun joriy texnologik qiymatni kiriting ({datchik['min']} — {datchik['max']} {datchik['unit']}):"
            
            reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            reply_markup.add("Ortga")
            bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=reply_markup)
        bot.answer_callback_query(call.id)

# ==========================================
# 4. SERVER VA BOTNI ISHGA TUSHIRISH
# ==========================================
if __name__ == "__main__":
    # Botni parallel oqimda (Thread) yurgizamiz
    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Flask veb-serverini Render portida ishga tushiramiz
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
