import pandas as pd
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# =========================
# EXCEL FILE
# =========================

EXCEL_FILE = "Indorama IO legend.xlsx"

# =========================
# EXCEL LOAD
# =========================

xls = pd.ExcelFile(EXCEL_FILE)

all_data = []

for sheet in xls.sheet_names:
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
        df = df.fillna("")
        df["__sheet__"] = sheet
        all_data.append(df)
    except:
        pass

full_df = pd.concat(all_data, ignore_index=True)

print("Excel loaded successfully")

# =========================
# SEARCH FUNCTION
# =========================

def search_data(query):

    query = str(query).lower()

    results = full_df[
        full_df.astype(str)
        .apply(lambda col: col.str.lower().str.contains(query, na=False))
        .any(axis=1)
    ]

    if results.empty:
        return "❌ Ma'lumot topilmadi"

    messages = []

    for _, row in results.head(5).iterrows():

        text = f"""
🔎 TAG:
{row.get('DCS TAGS ', '')}

📌 SERVICE:
{row.get('SERVICE', '')}

📌 IOM TAG:
{row.get('IOM TAG', '')}

📌 CONTROLLER:
{row.get('CONTROLLER', '')}

📌 CHANNEL:
{row.get('CHANNEL NO', '')}

📌 FTB CABINET:
{row.get('FTB CABINET', '')}

📌 FTB NAME:
{row.get('FTB NAME', '')}

📌 TB:
TB1 = {row.get('FTB1', '')}
TB2 = {row.get('FTB2', '')}

📌 SHEET:
{row.get('__sheet__', '')}
"""

        messages.append(text)

    return "\n\n".join(messages)

# =========================
# BOT TOKEN
# =========================

BOT_TOKEN = "8896826475:AAE_Z0W7Rhm6ynHH2a0smKjTyvXjW9GlLFM"

# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Smart KPIA Bot ishga tushdi!\n\nTag yuboring..."
    )

# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.message.text

    result = search_data(query)

    await update.message.reply_text(result)

# =========================
# APP
# =========================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)

print("Bot ishlayapti...")

app.run_polling()
