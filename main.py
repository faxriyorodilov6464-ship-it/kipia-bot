import os
import re
import pandas as pd
from telebot import TeleBot, types

# 1. BOT TOKENINI SOZLASH (Render uchun Environment Variable yoki to'g'ridan-to'g'ri token)
# Bu yerga o'z bot tokeningizni yozing yoki Render Config-ga joylang
TOKEN = os.getenv("BOT_TOKEN", "7358787834:AAEbO-YourActualTokenHere")
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
            
            # Ustun nomlarini boshliqlarsiz va katta harfga o'tkazamiz (tekshirish oson bo'lishi uchun)
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Tag ustunini aniqlash (turli sahifalarda har xil yozilgan bo'lishi mumkin)
            tag_col = None
            for col in df.columns:
                if "TAG" in col:
                    tag_col = col
                    break
            
            if not tag_col:
                continue  # Agar sahifada TAG ustuni bo'lmasa, o'tkazib yuboramiz

            # Har bir qatorni tahlil qilamiz
            for _, row in df.iterrows():
                tag_val = str(row[tag_col]).strip()
                if not tag_val or tag_val.lower() in ['nan', 'none', '']:
                    continue
                
                # Tegning o'zini qidiruv kaliti sifatida tozalaymiz
                clean_tag = re.sub(r'[^A-Z0-9-]', '', tag_val.upper())
                
                # Ma'lumotlarni yig'ish (kalitlar mosligiga qarab)
                description = ""
                for col in df.columns:
                    if "DESC" in col or "TAVSIF" in col:
                        description = str(row[col]).strip()
                        break
                
                # Diapazonlarni aniqlash (Min, Max, Unit)
                min_val, max_val, unit_val = None, None, ""
                
                for col in df.columns:
                    if "MIN" in col:
                        try: min_val = float(row[col])
                        except: pass
                    elif "MAX" in col:
                        try: max_val = float(row[col])
                        except: pass
                    elif "UNIT" in col or "BIRLIK" in col:
                        unit_val = str(row[col]).strip()

                # Agar alohida Min/Max bo'lmay, RANGE ustunida berilgan bo'lsa (masalan: 0-100)
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

                # Qolgan foydali ustunlarni ham matnga qo'shish uchun yig'amiz
                boshqa_malumotlar = []
                for col in df.columns:
                    if col not in [tag_col] and "DESC" not in col and "MIN" not in col and "MAX" not in col:
                        val = str(row[col]).strip()
                        if val and val.lower() != 'nan':
                            boshqa_malumotlar.append(f"<b>{col}:</b> {val}")

                # Bazaga saqlash
                db_datchiklar[clean_tag] = {
                    "original_tag": tag_val,
                    "sheet": sheet_name,
                    "description": description if description and description.lower() != 'nan' else "Kiritilmagan",
                    "min": min_val,
                    "max": max_val,
                    "unit": unit_val if unit_val.lower() != 'nan' else "",
                    "extra": "\n".join(boshqa_malumotlar)
                }
        print(f"Baza muvaffaqiyatli yuklandi! Jami datchiklar: {len(db_datchiklar)}")
    except Exception as e:
        print(f"Excelni o'qishda xatolik: {e}")

# Botni ishga tushirishda bazani yuklaymiz
load_excel_data()

# Foydalanuvchilar holatini saqlash uchun vaqtinchalik xotira
user_states = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 <b>Salom! KIPiA loyiha botiga xush kelibsiz!</b>\n\n"
        "🔍 Datchik haqida ma'lumot olish uchun uning <b>Tag raqamini</b> yozing.\n"
        "<i>Masalan: 101-FT-001</i>\n\n"
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

    # Agar foydalanuvchi hisob-kitob rejimida bo'lsa
    if chat_id in user_states:
        state = user_states[chat_id]
        mode = state["mode"]
        tag_key = state["tag"]
        datchik = db_datchiklar[tag_key]
        
        # Hisobdan chiqish tekshiruvi
        if text.lower() in ['ortqqa', 'back', 'bekor qilish', 'cancel', 'ortga']:
            del user_states[chat_id]
            bot.send_message(chat_id, "⚙️ Qidiruv rejimiga qaytdingiz. Yangi Tag kiritishingiz mumkin.")
            return

        try:
            val = float(text.replace(",", ".")) # Vergul ishlatilgan bo'lsa nuqtaga o'giradi
            Min = datchik["min"]
            Max = datchik["max"]
            Unit = datchik["unit"]

            if mode == "ma_to_val":
                if not (4 <= val <= 20):
                    bot.send_message(chat_id, "⚠️ Oqim qiymati 4 va 20 mA orasida bo'lishi kerak! Qaytadan kiriting:")
                    return
                # Formula: Qiymat = ((mA - 4) / 16) * (Max - Min) + Min
                natija = ((val - 4) / 16) * (Max - Min) + Min
                javob = f"📊 <b>Hisob natijasi:</b>\n\n" \
                        f"🔌 Kiritilgan oqim: <code>{val} mA</code>\n" \
                        f"📈 Hisoblangan qiymat: <b>{natija:.3f} {Unit}</b>"
                
            elif mode == "val_to_ma":
                if not (Min <= val <= Max) and Min != Max:
                    # Agar kiritilgan qiymat diapazondan tashqarida bo'lsa ogohlantiramiz, lekin hisoblaymiz
                    bot.send_message(chat_id, f"⚠️ Diqqat! Kiritilgan qiymat diapazondan ({Min} - {Max}) tashqarida.")
                
                # Formula: mA = ((Qiymat - Min) / (Max - Min)) * 16 + 4
                if Max - Min == 0:
                    natija_ma = 4.0
                else:
                    natija_ma = ((val - Min) / (Max - Min)) * 16 + 4
                
                javob = f"📊 <b>Hisob natijasi:</b>\n\n" \
                        f"📈 Kiritilgan qiymat: <code>{val} {Unit}</code>\n" \
                        f"🔌 Hisoblangan oqim: <b>{natija_ma:.3f} mA</b>"

            bot.send_message(chat_id, javob, parse_mode="HTML")
            del user_states[chat_id] # Hisob tugagach holatni o'chiramiz
            
            # Qayta hisoblash yoki ortga qaytish tugmasi
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("🔄 Qayta hisoblash", callback_data=f"calc_{mode}_{tag_key}"),
                types.InlineKeyboardButton("🔍 Yangi qidiruv", callback_data="new_search")
            )
            bot.send_message(chat_id, "Yana biror narsani hisoblaymizmi?", reply_markup=markup)

        except ValueError:
            bot.send_message(chat_id, "❌ Iltimos, faqat raqam kiriting (masalan: 12 yoki 5.5):")
        return

    # Standart holat: Datchik qidirish
    clean_text = re.sub(r'[^A-Z0-9-]', '', text.upper())

    if clean_text in db_datchiklar:
        datchik = db_datchiklar[clean_text]
        
        javob = f"📋 <b>Datchik topildi!</b>\n\n" \
                f"🏷 <b>Tag:</b> <code>{datchik['original_tag']}</code>\n" \
                f"🗂 <b>Sahifa:</b> {datchik['sheet']}\n" \
                f"📝 <b>Tavsif:</b> {datchik['description']}\n"
        
        if datchik["min"] is not None and datchik["max"] is not None:
            javob += f"🔢 <b>Diapazon:</b> {datchik['min']} - {datchik['max']} {datchik['unit']}\n"
        
        if datchik["extra"]:
            javob += f"\n⚙️ <b>Qo'shimcha ma'lumotlar:</b>\n{datchik['extra']}"

        # Agar datchik analog bo'lsa, kalkulyator tugmalarini chiqaramiz
        markup = types.InlineKeyboardMarkup()
        if datchik["min"] is not None and datchik["max"] is not None:
            btn1 = types.InlineKeyboardButton("🔌 mA ➡️ Qiymat", callback_data=f"calc_ma_to_val_{clean_text}")
            btn2 = types.InlineKeyboardButton("📈 Qiymat ➡️ mA", callback_data=f"calc_val_to_ma_{clean_text}")
            markup.row(btn1, btn2)
        
        bot.send_message(chat_id, javob, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"❌ Kechirasiz, bazadan <b>{text}</b> topilmadi. Qayta tekshirib ko'ring.", parse_mode="HTML")

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
        parts = data.split("_")
        # format: calc_mode_tag yoki calc_ma_to_val_tag
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
                msg = f"🔌 <b>[mA ➡️ Qiymat]</b>\n\n<code>{datchik['original_tag']}</code> datchigi uchun oqim qiymatini kiriting (4-20 mA orasida):"
            else:
                msg = f"📈 <b>[Qiymat ➡️ mA]</b>\n\n<code>{datchik['original_tag']}</code> datchigi uchun texnologik qiymatni kiriting ({datchik['min']} - {datchik['max']} {datchik['unit']}):"
            
            # Bekor qilish tugmasi bilan klaviatura
            reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            reply_markup.add("Ortga")
            
            bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=reply_markup)
        else:
            bot.send_message(chat_id, "❌ Xatolik: Datchik ma'lumotlari eskirgan.")
        
        bot.answer_callback_query(call.id)

if __name__ == "__main__":
    # Render yoki boshqa serverda 24/7 ishlashi uchun poatgacha tekshiradi
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling()

