import os
import requests
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

RENDER_APP = "tg-gofile-bot"  # change if your Render app name is different
PORT = int(os.getenv("PORT", 10000))
webhook_url = f"https://{RENDER_APP}.onrender.com/{BOT_TOKEN}"

# --- Helpers ---
def extract_folder_id(url):
    path = urlparse(url).path
    return path.rstrip('/').split('/')[-1]

def get_gofile_txt_files(folder_url):
    folder_id = extract_folder_id(folder_url)
    api_url = f"https://api.gofile.io/getContent?contentId={folder_id}&includeDownloadLinks=true"
    try:
        r = requests.get(api_url, timeout=15)
        r.raise_for_status()

        # Detect traffic limit / cold storage messages in HTML
        if "Traffic limit exceeded" in r.text or "cold storage" in r.text.lower():
            print("⚠️ Gofile folder is restricted due to traffic limit or cold storage.")
            return "traffic_limit"

        data = r.json()
    except ValueError:
        print(f"❌ Gofile API did not return JSON. Status: {r.status_code}, Body: {r.text[:200]}")
        return []
    except Exception as e:
        print(f"❌ Error fetching/parsing Gofile API: {e}")
        return []

    if data.get("status") != "ok":
        print(f"❌ Gofile API returned error: {data}")
        return []

    return [f for f in data["data"]["contents"].values()
            if f["type"] == "file" and f["name"].endswith(".txt")]

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a Gofile folder link and I’ll send all .txt files one by one."
    )

async def handle_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("https://gofile.io/d/"):
        await update.message.reply_text("⚠️ Please send a valid Gofile folder link.")
        return

    await update.message.reply_text("🔍 Fetching .txt files from folder...")
    txt_files = get_gofile_txt_files(url)

    if txt_files == "traffic_limit":
        await update.message.reply_text(
            "⚠️ This Gofile folder is temporarily unavailable due to traffic limits or cold storage.\n"
            "Try again later or use a premium account."
        )
        return

    if not txt_files:
        await update.message.reply_text("❌ No .txt files found or folder is invalid.")
        return

    for f in txt_files:
        try:
            data = requests.get(f["link"], timeout=30).content
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=data,
                filename=f["name"],
                caption=f"📄 `{f['name']}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to send {f['name']}: {e}")

# --- Post-init hook to set webhook ---
async def post_init(app):
    await app.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_folder))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url
    )
