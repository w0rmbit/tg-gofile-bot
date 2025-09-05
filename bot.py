import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

RENDER_APP = "tg-gofile-bot"  # change if your Render app name is different
PORT = int(os.getenv("PORT", 10000))

# --- Gofile Folder Parser ---
def get_gofile_txt_files(folder_url):
    folder_id = folder_url.strip().split('/')[-1]
    api_url = f"https://api.gofile.io/getContent?contentId={folder_id}&includeDownloadLinks=true"
    r = requests.get(api_url).json()
    if r.get("status") != "ok":
        return []
    return [f for f in r["data"]["contents"].values() if f["type"] == "file" and f["name"].endswith(".txt")]

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a Gofile folder link and I’ll send all .txt files one by one.")

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

    for f in txt_files:
        try:
            data = requests.get(f["link"]).content
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=data,
                filename=f["name"],
                caption=f"📄 `{f['name']}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to send {f['name']}: {e}")

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_folder))

    webhook_url = f"https://{RENDER_APP}.onrender.com/{BOT_TOKEN}"
    print(f"Setting webhook to: {webhook_url}")
    app.bot.set_webhook(url=webhook_url)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url
    )
