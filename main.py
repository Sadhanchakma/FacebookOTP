import os
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from openai import OpenAI

# ================= ENV =================
TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# ================= HF CLIENT =================
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# ================= FLASK (RENDER KEEP ALIVE) =================
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

# ================= DATA =================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def user_file(uid):
    return f"{DATA_DIR}/{uid}.txt"

# ================= AI CHAT =================
async def ask_ai(text):
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[{"role": "user", "content": text}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return "❌ AI Error"

# ================= UPLOAD =================
async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    path = user_file(uid)

    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ TXT only")
        return

    file = await doc.get_file()
    temp = f"{uid}_tmp.txt"
    await file.download_to_drive(temp)

    with open(temp) as f:
        new = f.readlines()

    with open(path, "a") as f:
        f.writelines(new)

    os.remove(temp)

    await update.message.reply_text(f"✅ Added {len(new)} OTP")

# ================= GET OTP =================
def get_next(uid):
    path = user_file(uid)

    if not os.path.exists(path):
        return None

    with open(path) as f:
        lines = f.readlines()

    if not lines:
        os.remove(path)
        return None

    line = lines[0].strip()

    with open(path, "w") as f:
        f.writelines(lines[1:])

    num, otp = [x.strip() for x in line.split("|")]
    return num, otp, len(lines)

def format_text(num, otp, left):
    return f"""
╔═══ 📲 OTP RESULT ═══╗
📱 Number: `{num}`
🔐 OTP   : `{otp}`
📊 Left  : {left}
╚════════════════════╝
"""

async def send(update, context, edit=False):
    uid = update.effective_user.id
    data = get_next(uid)

    if not data:
        text = "❌ No OTP left"
        if edit:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    num, otp, total = data

    kb = [[InlineKeyboardButton("🔄 NEXT", callback_data="n")]]
    markup = InlineKeyboardMarkup(kb)

    text = format_text(num, otp, total-1)

    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

# ================= SEARCH / AI =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    path = user_file(uid)

    q = update.message.text.strip()

    # OTP search first
    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()

        for line in lines:
            if q in line:
                num, otp = [x.strip() for x in line.split("|")]
                await update.message.reply_text(
                    f"🔍 FOUND\n\n📱 `{num}`\n🔐 `{otp}`",
                    parse_mode="Markdown"
                )
                return

    # If not found → AI response
    ai = await ask_ai(q)
    await update.message.reply_text(ai)

# ================= MENU =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📲 Get Number":
        await send(update, context)

    elif text == "🗑️ Delete":
        await delete(update, context)

    elif text == "📤 Upload":
        await update.message.reply_text("📤 TXT file send করো")

    else:
        await search(update, context)

# ================= BUTTON =================
async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "n":
        await send(update, context, edit=True)

# ================= COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📲 Get Number", "🗑️ Delete"],
        ["📤 Upload"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "স্বাগতম! নিচের মেনু থেকে অপশন সিলেক্ট করুন:",
        reply_markup=reply_markup
    )

async def get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, context)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = user_file(update.effective_user.id)
    if os.path.exists(path):
        os.remove(path)
        await update.message.reply_text("🗑️ Deleted")
    else:
        await update.message.reply_text("❌ No file")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get))
    app.add_handler(CommandHandler("delete", delete))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(btn))

    print("✅ Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
