import os
import json
import base64
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/seen_songs.json"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

def load_seen_songs():
    r = requests.get(GITHUB_API, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        raw = json.loads(content)
        songs = []
        for item in raw:
            songs.append({"key": item} if isinstance(item, str) else item)
        return songs, data["sha"]
    return [], None

def save_seen_songs(songs, sha):
    content = base64.b64encode(json.dumps(songs, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    payload = {"message": "update seen songs", "content": content}
    if sha:
        payload["sha"] = sha
    r = requests.put(GITHUB_API, headers=HEADERS, json=payload)
    return r.json().get("content", {}).get("sha")

seen_songs, current_sha = load_seen_songs()
pending = {}
pending_counter = 0

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Health).serve_forever()

def already_seen(key):
    return any(s["key"] == key for s in seen_songs)

async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip().lower()
    if not query:
        await update.message.reply_text("اسم آهنگ رو بعد از /search بنویس.")
        return
    matches = [s["key"] for s in seen_songs if query in s["key"]]
    if not matches:
        await update.message.reply_text("❌ همچین آهنگی تو لیست نیست.")
        return
    lines = []
    for m in matches[:10]:
        title, _, performer = m.partition("|")
        lines.append(f"• {title} - {performer}" if performer else f"• {title}")
    await update.message.reply_text("✅ اینا رو پیدا کردم:\n" + "\n".join(lines))

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_sha
    query = update.callback_query
    await query.answer()
    action, _, token = query.data.partition(":")
    item = pending.pop(token, None)

    if not item:
        await query.edit_message_text("⏱ این درخواست منقضی شده، دوباره آهنگ رو بفرست.")
        return
    if action == "cancel":
        await query.edit_message_text("❌ لغو شد.")
        return

    try:
        await context.bot.send_audio(chat_id=TARGET_CHANNEL_ID, audio=item["file_id"], caption=item["caption"])
        await query.edit_message_text("✅ اهنگ فرستاده شد!")
    except Exception as e:
        await query.edit_message_text(f"❌ نشد بفرستم: {e}")
        return

    if item["key"]:
        try:
            seen_songs.append({"key": item["key"]})
            current_sha = save_seen_songs(seen_songs, current_sha)
        except Exception:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_counter
    msg = update.message
    audio = msg.audio
    doc = msg.document

    if not (audio or doc):
        await msg.reply_text(f"آی‌دی این چت: {update.effective_chat.id}")
        return

    file_id = audio.file_id if audio else doc.file_id
    key = None
    if audio and audio.title:
        key = f"{audio.title.strip().lower()}|{(audio.performer or '').strip().lower()}"

    if key and already_seen(key):
        await msg.reply_text("⚠️ این آهنگ قبلاً فرستاده شده!")
        return

    caption = None
    if audio and audio.title:
        caption = f"{audio.title} - {audio.performer}" if audio.performer else audio.title

    pending_counter += 1
    token = str(pending_counter)
    pending[token] = {"file_id": file_id, "caption": caption, "key": key}

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ بفرست", callback_data=f"confirm:{token}"),
        InlineKeyboardButton("❌ لغو", callback_data=f"cancel:{token}"),
    ]])
    await msg.reply_text("این آهنگ فرستاده بشه؟", reply_markup=keyboard)

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("search", search_song))
    app.add_handler(CallbackQueryHandler(handle_confirmation))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
