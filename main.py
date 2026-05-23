import os
import pandas as pd
import telebot

# Bot tokenini kiriting (Render'da Environment Variable qilib kiritgan bo'lsangiz o'sha nomni yozing)
TOKEN = os.environ.get('BOT_TOKEN', 'Sizning_Bot_Tokeningiz_Bu_Yerga')
bot = telebot.TeleBot(TOKEN)

# Excel fayl nomi (GitHub'dagi fayl nomi bilan 100% bir xil bo'lsin)
EXCEL_FILE = 'Indorama IO legend.xlsx'

def search_sensor_in_excel(query):
    try:
        # Excelni o'qiymiz, barcha ustunlarni matn (string) formatida yuklaymiz
        df = pd.read_excel(EXCEL_FILE, dtype=str)
        
        # Ustun nomlaridagi ortiqcha bo'shliqlarni tozalaymiz
        df.columns = df.columns.str.strip()
        
        # Birinchi ustunni "Datchik nomi" (Tag) ustuni deb olamiz
        tag_column = df.columns[0]
        
        # Foydalanuvchi so'rovini qidirish uchun tayyorlaymiz (kichik harf, bo'shliqlarsiz)
        clean_query = query.strip().lower().replace('-', '').replace('_', '')
        
        # Excel'dagi birinchi ustunni ham qidirish uchun xuddi shunday formatga keltiramiz
        clean_tags = df[tag_column].str.strip().str.lower().str.replace('-', '', regex=False).str.replace('_', '', regex=False)
        
        # To'g'ridan-to'g'ri mos keladigan qatorni topamiz
        matched_rows = df[clean_tags == clean_query]
        
        # Agar aniq moslik topilmasa, qisman qidirib ko'ramiz (masalan, faqat raqamini yozsa ham)
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
    
    # Exceldan qidirish
    results = search_sensor_in_excel(user_text)
    
    if results is None:
        bot.reply_to(message, "❌ Tizimda xatolik yuz berdi. Excel fayli topilmadi yoki shikastlangan.")
        return

    if not results.empty:
        # Faqat birinchi topilgan qatorni chiroyli qilib chiqaramiz
        row = results.iloc[0]
        
        response = "✅ **Datchik topildi!**\n"
        response += "-------------------------\n"
        
        # Excel'dagi barcha ustunlarni ketma-ket chiqarish (dinamik holatda)
        for column in results.columns:
            # Agar katak bo'sh bo'lsa (NaN), "Mavjud emas" deb ko'rsatadi
            val = row[column] if pd.notna(row[column]) else "Ma'lumot yo'q"
            response += f"🔹 **{column}:** {val}\n"
            
        bot.reply_to(message, response, parse_mode="Markdown")
    else:
        bot.reply_to(
            message, 
            f"❌ Kechirasiz, bazadan **{user_text}** nomli datchik topilmadi.\n"
            f"Iltimos, nomni to'g'ri yozganingizni tekshiring.",
            parse_mode="Markdown"
        )

if __name__ == '__main__':
    print("Bot ishga tushdi...")
    bot.infinity_polling()
