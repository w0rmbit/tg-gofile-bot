import os
import requests
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# --- Flask App for Health Check & Webhook ---
app = Flask(__name__)

@app.route('/')
def health():
    return "OK", 200

@app.route(f"/{os.getenv('BOT_TOKEN')}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port)

# --- Telegram Bot Setup ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN is not set.")
    exit(1)

# --- Gofile Folder Parser ---
def get_gofile_txt_files(folder_url):
    folder_id = folder_url.strip().split('/')[-1]
    api_url = f"https://api.gofile.io/getContent?contentId={folder_id}&includeDownloadLinks=true"
    response = requests.get(api_url).json()

    if response.get("status") != "ok":
        return []

    contents = response["data"]["contents"]
    txt_files = [
        file for file in contents.values()
        if file["type"] == "file" and file["name"].endswith(".txt")
    ]
    return txt_files

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a Gofile folder link and I’ll send you all .txt files one by one."
    )

async def handle_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("https://gofile.io/d/"):
        await update.message.reply_text("⚠️ Please send a valid Gofile folder link.")
        return

    await update.message.reply_text("🔍 Fetching .txt files from folder...")
    txt_files = get_gofile_txt_files(url)

    if not txt_files:
        await update.message.reply_text("❌ No .txt files found or folder is invalid.")
        return

    for file in txt_files:
        try:
            file_data = requests.get(file["link"]).content
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_data,
                filename=file["name"],
                caption=f"📄 `{file['name']}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to send `{file['name']}`: {e}")

# --- Run Bot + Flask ---
if __name__ == "__main__":
    print("🤖 Bot is running with Flask health check + webhook...")

    # Build bot app
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_folder))

    # Start Flask in a separate thread
    threading.Thread(target=run_flask).start()

    # Set webhook URL (replace YOUR_RENDER_APP_NAME)
    webhook_url = f"https://YOUR_RENDER_APP_NAME.onrender.com/{BOT_TOKEN}"
    bot_app.bot.set_webhook(url=webhook_url)

    # Start processing updates from webhook
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=webhook_url
    )
