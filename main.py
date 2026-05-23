import os
import threading
import pandas as pd
import telebot
from flask import Flask

# 1. Flask veb-serverini yaratamiz (Render o'chib qolmasligi uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Botni sozlaymiz
RAW_TOKEN = os.environ.get('BOT_TOKEN', '8896826475:AAE_Z0W7Rhm6ynHH2a0smKjTyvXjW9GlLFM')
TOKEN = "".join(RAW_TOKEN.split()).strip()

bot = telebot.TeleBot(TOKEN)

EXCEL_FILE = 'Indorama IO legend.xlsx'

def search_sensor_in_excel(query):
    try:
        # Excel faylni to'liq o'qiymiz
        df = pd.read_excel(EXCEL_FILE, dtype=str)
        
        # Ustun nomlaridagi bo'shliqlarni tozalaymiz
        df.columns = df.columns.str.strip()
        
        # Foydalanuvchi yozgan matnni tozalaymiz (faqat harf va raqamlar qoladi, kichik harfda)
        clean_query = "".join(c for c in query if c.isalnum()).lower()
        
        if not clean_query:
            return None
            
        # Excel'dagi barcha ustunlar bo'ylab qidiramiz (istalgan ustundan topa oladi)
        for column in df.columns:
            # Ustundagi qiymatlarni tozalab solishtiramiz
            clean_tags = df[column].astype(str).apply(lambda val: "".join(c for c in val if c.isalnum()).lower())
            
            # 1-Urinish: Aniq mos kelishini tekshirish
            matched_rows = df[clean_tags == clean_query]
            
            # 2-Urinish: Agar aniq mos kelmasa, matn ichida qisman borligini tekshirish (contains)
            if matched_rows.empty:
                matched_rows = df[clean_tags.str.contains(clean_query, na=False)]
                
            # 3-Urinish: Agar I va L harflari chalkashgan bo'lsa, ularni almashtirib tekshirish
            if matched_rows.empty:
                flex_query = clean_query.replace('l', 'i')
                flex_tags = clean_tags.str.replace('l', 'i')
                matched_rows = df[flex_tags == flex_query]
                
            # Agar ushbu ustundan ma'lumot topilsa, natijani qaytaramiz va qidiruvni to'xtatamiz
            if not matched_rows.empty:
                return matched_rows
                
        return pd.DataFrame() # Agar hech qaysi ustundan topilmasa, bo'sh qaytaradi
        
    except Exception as e:
        print(f"Excelni o'qishda xatolik: {e}")
        return None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 **Smart KPIA Botiga xush kelibsiz!**\n\n"
        "Menga istalgan datchik nomini yuboring. Men uni bazadan qidirib, "
        "barcha ma'lumotlarini topib beraman."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    user_text = message.text # <--- Foydalanuvchi aynan nima yozsa, o'shani oladi!
    
    # Exceldan qidirish funksiyasiga foydalanuvchi matnini uzatamiz
    results = search_sensor_in_excel(user_text)
    
    if results is None:
        bot.reply_to(message, "❌ Tizimda xatolik yuz berdi. Excel fayli topilmadi yoki shikastlangan.")
        return

    if not results.empty:
        row = results.iloc[0]
        response = f"✅ **Ma'lumot topildi! (Siz yozgan so'rov: {user_text})**\n"
        response += "-------------------------\n"
        
        # Excel'dagi barcha ustunlarni ketma-ket chiqarish
        for column in results.columns:
            val = row[column] if pd.notna(row[column]) else "Ma'lumot yo'q"
            response += f"🔹 **{column}:** {val}\n"
            
        bot.reply_to(message, response, parse_mode="Markdown")
    else:
        bot.reply_to(
            message, 
            f"❌ Kechirasiz, bazadan **{user_text}** haqida hech qanday ma'lumot topilmadi.\n"
            f"Iltimos, nomni to'g'ri yozganingizni tekshiring.",
            parse_mode="Markdown"
        )

# 3. Server va Botni parallel ravishda ishga tushiramiz
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Bot polling rejimida ishga tushdi...")
    bot.infinity_polling()
