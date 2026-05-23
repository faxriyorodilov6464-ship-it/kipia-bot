import os
import threading
import pandas as pd
import telebot
from flask import Flask

# 1. Flask veb-serverini yaratamiz (Render port xatoligi bermasligi uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    # Render avtomatik ravishda PORT muhit o'zgaruvchisini beradi
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Botni sozlaymiz
TOKEN = os.environ.get('BOT_TOKEN', 'Sizning_Bot_Tokeningiz_Bu_Yerga')
bot = telebot.TeleBot(TOKEN)

EXCEL_FILE = 'Indorama IO legend.xlsx'

def search_sensor_in_excel(query):
    try:
        df = pd.read_excel(EXCEL_FILE, dtype=str)
        df.columns = df.columns.str.strip()
        tag_column = df.columns[0]
        
        clean_query = query.strip().lower().replace('-', '').replace('_', '')
        clean_tags = df[tag_column].str.strip().str.lower().str.replace('-', '', regex=False).str.replace('_', '', regex=False)
        
        matched_rows = df[clean_tags == clean_query]
        if matched_rows.empty:
            matched_rows = df[clean_tags.str.contains(clean_query, na=False, regex=False)]
            
        return matched_rows
    except Exception as e:
        print(f"Excelni o'qishda xatolik: {e}")
        return None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 **Smart KPIA Botiga xush kelibsiz!**\n\n"
        "Menga datchik nomini yuboring (Masalan: `276_LI_51` yoki `271-PI-79`), "
        "men sizga u haqidagi barcha ma'lumotlarni bazadan topib beraman."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    user_text = message.text
    results = search_sensor_in_excel(user_text)
    
    if results is None:
        bot.reply_to(message, "❌ Tizimda xatolik yuz berdi. Excel fayli topilmadi yoki shikastlangan.")
        return

    if not results.empty:
        row = results.iloc[0]
        response = "✅ **Datchik topildi!**\n"
        response += "-------------------------\n"
        
        for column in results.columns:
            val = row[column] if pd.notna(row[column]) else "Ma'lumot yo'q"
            response += f"🔹 **{column}:** {val}\n"
            
        bot.reply_to(message, response, parse_mode="Markdown")
    else:
        bot.reply_to(
            message, 
            f"❌ Kechirasiz, bazadan **{user_text}** nomli datchik topilmadi.",
            parse_mode="Markdown"
        )

# 3. Server va Botni parallel ravishda ishga tushiramiz
if __name__ == '__main__':
    # Flask serverini alohida oqimda (thread) ishga tushiramiz
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Bot polling rejimida ishga tushdi...")
    bot.infinity_polling()
