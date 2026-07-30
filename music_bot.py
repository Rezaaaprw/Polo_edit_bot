import os
import json
import base64
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

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
        return json.loads(content), data["sha"]
    return [], None

def save_seen_songs(songs, sha):
    content = base64.b64encode(json.dumps(songs, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    payload = {"message": "update seen songs", "content": content}
    if sha:
        payload["sha"] = sha
    r = requests.put(GITHUB_API, headers=HEADERS, json=payload)
    return r.json().get("content", {}).get("sha")

seen_songs, current_sha = load_seen_songs()

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Health).serve_forever()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_sha
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

    if key and key in seen_songs:
        await msg.reply_text("⚠️ این آهنگ قبلاً فرستاده شده!")
        return

    caption = None
    if audio and audio.title:
        caption = f"{audio.title} - {audio.performer}" if audio.performer else audio.title

    try:
        await context.bot.send_audio(chat_id=TARGET_CHANNEL_ID, audio=file_id, caption=caption)
        await msg.reply_text("✅ اهنگ فرستاده شد!")
    except Exception as e:
        await msg.reply_text(f"❌ نشد بفرستم: {e}")
        return

    if key:
        try:
            seen_songs.append(key)
            current_sha = save_seen_songs(seen_songs, current_sha)
        except Exception:
            pass

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
