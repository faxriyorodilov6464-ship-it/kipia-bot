import os
import re
import threading
import pandas as pd
from telebot import TeleBot, types
from flask import Flask

# ==========================================
# 1. FLASK VEB-SERVER (Render port xatosini yo'qotish uchun)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Smart KPIA Bot is live and healthy!"

def run_flask():
    # Render o'zi beradigan PORT muhit o'zgaruvchisini majburiy o'qiymiz
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. BOT TOKENINI VA EXCELNI SOZLASH
# ==========================================
# Siz bergan yangi va haqiqiy tokeningizni shu yerga joyladim
TOKEN = "8896826475:AAE_Z0W7Rhm6ynHH2a0smKjTyvXjW9GlLFM"
bot = TeleBot(TOKEN)

EXCEL_FILE = "Indorama IO legend.xlsx"
db_datchiklar = {}

def load_excel_data():
    """Excel faylidagi barcha varaqlarni o'qib, umumiy bazaga yig'adi"""
    global db_datchiklar
    db_datchiklar.clear()
    
    if not os.path.exists(EXCEL_FILE):
        print(f"Xatolik: '{EXCEL_FILE}' fayli topilmadi!")
        return

    try:
        xls = pd.ExcelFile(EXCEL_FILE)
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            tag_col = None
            for col in df.columns:
                if "TAG" in col:
                    tag_col = col
                    break
            
            if not tag_col:
                continue

            for _, row in df.iterrows():
                tag_val = str(row[tag_col]).strip()
                if not tag_val or tag_val.lower() in ['nan', 'none', '']:
                    continue
                
                clean_tag = re.sub(r'[^A-Z0-9-]', '', tag_val.upper())
                
                description = ""
                for col in df.columns:
                    if "DESC" in col or "TAVSIF" in col:
                        description = str(row[col]).strip()
                        break
                
                min_val, max_val, unit_val = None, None, ""
                for col in df.columns:
                    if "MIN" in col or "LOW" in col:
                        try: min_val = float(row[col])
                        except: pass
                    elif "MAX" in col or "HIGH" in col:
                        try: max_val = float(row[col])
                        except: pass
                    elif "UNIT" in col or "BIRLIK" in col:
                        unit_val = str(row[col]).strip()

                if min_val is None or max_val is None:
                    for col in df.columns:
                        if "RANGE" in col or "DIAPAZON" in col:
                            range_text = str(row[col]).strip()
                            match = re.findall(r"[-+]?\d*\.\d+|\d+", range_text)
                            if len(match) >= 2:
                                try:
                                    min_val = float(match[0])
                                    max_val = float(match[1])
                                except: pass
                            break

                boshqa_malumotlar = []
                for col in df.columns:
                    if col not in [tag_col] and "DESC" not in col and "MIN" not in col and "MAX" not in col and "LOW" not in col and "HIGH" not in col:
                        val = str(row[col]).strip()
                        if val and val.lower() != 'nan':
                            boshqa_malumotlar.append(f"<b>{col}:</b> {val}")

                db_datchiklar[clean_tag] = {
                    "original_tag": tag_val,
                    "sheet": sheet_name,
                    "description": description if description and description.lower() != 'nan' else "Kiritilmagan",
                    "min": min_val,
                    "max": max_val,
                    "unit": unit_val if unit_val.lower() != 'nan' else "",
                    "extra": "\n".join(boshqa_malumotlar[:6])
                }
        print(f"Baza yuklandi. Jami: {len(db_datchiklar)}")
    except Exception as e:
        print(f"Excel xatolik: {e}")

load_excel_data()
user_states = {}

# ==========================================
# 3. TELEGRAM BOT BUYRUQLARI
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 <b>Salom Faxriyor! Smart KPIA Botiga xush kelibsiz!</b>\n\n"
        "🔍 Datchik haqida ma'lumot olish uchun uning <b>Tag raqamini</b> yozing.\n"
        "<i>Masalan: 21-PT-1108A</i>\n\n"
        "🔄 Bazani yangilash uchun /refresh buyrug'ini yuboring."
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['refresh'])
def refresh_database(message):
    load_excel_data()
    bot.reply_to(message, f"🔄 Baza qayta yuklandi! Jami datchiklar soni: {len(db_datchiklar)}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

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
                javob = f"📊 <b>Hisob natijasi:</b>\n\n🔌 Oqim: <code>{val} mA</code>\n📈 Qiymat: <b>{natija:.3f} {Unit}</b>"
                
            elif mode == "val_to_ma":
                if Max - Min == 0: natija_ma = 4.0
                else: nilai_ma = ((val - Min) / (Max - Min)) * 16 + 4
                javob = f"📊 <b>Hisob natijasi:</b>\n\n📈 Qiymat: <code>{val} {Unit}</code>\n🔌 Oqim: <b>{nilai_ma:.3f} mA</b>"

            bot.send_message(chat_id, javob, parse_mode="HTML")
            del user_states[chat_id]
            
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("🔄 Qayta hisoblash", callback_data=f"calc_{mode}_{tag_key}"),
                types.InlineKeyboardButton("🔍 Yangi qidiruv", callback_data="new_search")
            )
            bot.send_message(chat_id, "Yana hisoblaymizmi?", reply_markup=markup)
        except ValueError:
            bot.send_message(chat_id, "❌ Iltimos, faqat raqam kiriting:")
        return

    clean_text = re.sub(r'[^A-Z0-9-]', '', text.upper())

    if clean_text in db_datchiklar:
        datchik = db_datchiklar[clean_text]
        javob = f"📋 <b>Datchik topildi!</b>\n\n🏷 <b>Tag:</b> <code>{datchik['original_tag']}</code>\n🗂 <b>Sahifa:</b> {datchik['sheet']}\n📝 <b>Tavsif:</b> {datchik['description']}\n"
        
        if datchik["min"] is not None and datchik["max"] is not None:
            javob += f"🔢 <b>Diapazon:</b> {datchik['min']} - {datchik['max']} {datchik['unit']}\n"
        
        if datchik["extra"]:
            javob += f"\n⚙️ <b>Boshqa ma'lumotlar:</b>\n{datchik['extra']}"

        markup = types.InlineKeyboardMarkup()
        if datchik["min"] is not None and datchik["max"] is not None:
            btn1 = types.InlineKeyboardButton("🔌 mA ➡️ Qiymat", callback_data=f"calc_ma_to_val_{clean_text}")
            btn2 = types.InlineKeyboardButton("📈 Qiymat ➡️ mA", callback_data=f"calc_val_to_ma_{clean_text}")
            markup.row(btn1, btn2)
        
        bot.send_message(chat_id, javob, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"❌ Kechirasiz, bazadan <b>{text}</b> topilmadi.", parse_mode="HTML")

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
                msg = f"🔌 <b>[mA ➡️ Qiymat]</b>\n\n<code>{datchik['original_tag']}</code> oqimini kiriting (4-20 mA):"
            else:
                msg = f"📈 <b>[Qiymat ➡️ mA]</b>\n\n<code>{datchik['original_tag']}</code> qiymatini kiriting ({datchik['min']} - {datchik['max']} {datchik['unit']}):"
            
            reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            reply_markup.add("Ortga")
            bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=reply_markup)
        bot.answer_callback_query(call.id)

# ==========================================
# 4. SERVER VA BOTNI PARALLEL ISHGA TUSHIRISH
# ==========================================
if __name__ == "__main__":
    # 1. Bot so'rovlarini alohida oqimda (Thread) boshlaymiz
    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Render kutayotgan Flask serverini yurgizamiz
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
