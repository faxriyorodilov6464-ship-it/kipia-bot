import os
import telebot
from telebot import types

# Bot tokenini shu yerga yozing
BOT_TOKEN = "7889950612:AAH..."  # <--- O'zingizning haqiqiy bot tokeningizni qo'ying
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"Assalomu alaykum, {user_name}!\n\n"
        "🤖 **KIPiA bo'limi avtomatlashtirish botiga xush kelibsiz!**\n"
        "Bu bot datchiklar, kontrollerlar va metrologiya sohasiga oid "
        "ma'lumotlarni hisoblash va kuzatish uchun mo'ljallangan.\n\n"
        "Hozircha bot test rejimida ishlamoqda."
    )
    
    # Odd
