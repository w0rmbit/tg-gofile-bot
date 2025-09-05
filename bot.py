import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

def get_gofile_txt_files(folder_url):
    folder_id = folder_url.strip().split('/')[-1]
    api_url = f"https://api.gofile.io/getContent?contentId={folder_id}&includeDownloadLinks=true"
    r = requests.get(api_url).json()
    if r.get("status") != "ok":
        return []
    return [f for f in r["data"]["contents"].values() if f["type"] == "file" and f["name"].endswith(".txt")]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a Gofile folder link and I’ll send all .txt files.")

async def handle_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("https://gofile.io/d/"):
        await update.message.reply_text("⚠️ Invalid Gofile folder link.")
        return
    files = get_gofile_txt_files(url)
    if not files:
        await update.message.reply_text("❌ No .txt files found.")
        return
    for f in files:
        try:
            data = requests.get(f["link"]).content
            await context.bot.send_document(update.effective_chat.id, data, filename=f["name"])
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to send {f['name']}: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_folder))

    webhook_url = f"https://YOUR_RENDER_APP_NAME.onrender.com/{BOT_TOKEN}"
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=webhook_url
    )
