import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- CONFIG ---
TOKEN = "8565891108:AAGRgHofZaaDtE_gT7ca3gO3uM0v8HToh8s"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def user_file(uid):
    return f"{DATA_DIR}/{uid}.txt"

def used_file(uid):
    return f"{DATA_DIR}/{uid}_used.txt"

# ================= PARSER =================
def parse_line(line):
    parts = line.split("|")
    if len(parts) < 2:
        return None, None
    
    number = parts[0].strip()
    otp = parts[-1].strip()
    return number, otp

# ================= CORE =================
def get_next(uid):
    path = user_file(uid)
    used_path = used_file(uid)

    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        lines = f.readlines()

    if not lines:
        return None

    line = lines[0].strip()

    # 🔥 remove from main
    with open(path, "w") as f:
        f.writelines(lines[1:])

    # 🔥 save to used
    with open(used_path, "a") as f:
        f.write(line + "\n")

    num, otp = parse_line(line)
    if not num or not otp:
        return None

    return num, otp, len(lines)

async def send_otp_ui(update, context, edit=False):
    uid = update.effective_user.id
    data = get_next(uid)

    if not data:
        text = "❌ *No OTPs left in your database!*"
        if edit:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
        return

    num, otp, remaining = data
    text = (
        f"╔════ 📲 *OTP RESULT* ════╗\n"
        f" 📱 *Number:* `{num}`\n"
        f" 🔐 *OTP:* `{otp}`\n"
        f" 📊 *Left:* {remaining - 1}\n"
        f"╚════════════════════╝"
    )

    kb = [[InlineKeyboardButton("🔄 NEXT OTP", callback_data="next_otp")]]
    markup = InlineKeyboardMarkup(kb)

    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["⚡ GET OTP", "📊 MY STATS"],
        ["📤 UPLOAD", "🗑️ CLEAR ALL"],
        ["ℹ️ HELP"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✨ *OTP MANAGER BOT* ✨\n\nUse buttons below:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    doc = update.message.document
    
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Send .txt file only")
        return

    file = await doc.get_file()
    temp = f"{uid}.txt"
    await file.download_to_drive(temp)

    with open(temp) as f:
        new_lines = f.readlines()

    with open(user_file(uid), "a") as f:
        f.writelines(new_lines)

    os.remove(temp)
    await update.message.reply_text(f"✅ Added {len(new_lines)} OTPs")

async def menu_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "⚡ GET OTP":
        await send_otp_ui(update, context)

    elif text == "📊 MY STATS":
        count = 0
        if os.path.exists(user_file(uid)):
            with open(user_file(uid)) as f:
                count = len(f.readlines())
        await update.message.reply_text(f"📊 Remaining: {count}")

    elif text == "📤 UPLOAD":
        await update.message.reply_text("Send .txt file")

    elif text == "🗑️ CLEAR ALL":
        if os.path.exists(user_file(uid)):
            os.remove(user_file(uid))
        if os.path.exists(used_file(uid)):
            os.remove(used_file(uid))
        await update.message.reply_text("🗑️ Cleared")

    elif text == "ℹ️ HELP":
        await update.message.reply_text("Format: number | otp")

    else:
        # 🔥 SEARCH (main + used)
        found = False
        search = text.strip()

        for file_path in [user_file(uid), used_file(uid)]:
            if not os.path.exists(file_path):
                continue

            with open(file_path) as f:
                lines = f.readlines()

            for line in lines:
                num, otp = parse_line(line)
                if not num:
                    continue

                if search == num or search in num:
                    await update.message.reply_text(
                        f"🔍 FOUND\n\n📱 `{num}`\n🔐`{otp}`",
 			parse_mode="Markdown"
                    )
                    found = True
                    break

            if found:
                break

        if not found:
            await update.message.reply_text("❌ Not found")

async def callback_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next_otp":
        await send_otp_ui(update, context, edit=True)

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_logic))
    app.add_handler(CallbackQueryHandler(callback_btn))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
