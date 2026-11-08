import os
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "").strip()

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_TG_FILE = 20 * 1024 * 1024
ALLOWED_EXT = ("flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "opus", "wav", "webm")

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

def groq_transcribe(data, filename):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY تنظیم نشده")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        ext = "mp4"
    filename = "file." + ext
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        files={"file": (filename, data)},
        data={"model": "whisper-large-v3", "language": "fa", "response_format": "json"},
        
        timeout=120,
    )
    if r.status_code != 200:
        raise Exception(f"Groq {r.status_code}: {r.text[:200]}")
    return r.json().get("text", "").strip()

async def transcribe_and_reply(context, chat_id, file_id, filename, status_msg):
    try:
        tg_file = await context.bot.get_file(file_id)
        data = bytes(await tg_file.download_as_bytearray())
        text = await asyncio.to_thread(groq_transcribe, data, filename)
    except Exception as e:
        await status_msg.edit_text(f"❌ نشد تبدیل کنم: {str(e)[:300]}")
        return
    if not text:
        await status_msg.edit_text("متنی توی این فایل پیدا نشد.")
        return
    await status_msg.delete()
    for i in range(0, len(text), 4000):
        await context.bot.send_message(chat_id=chat_id, text=text[i:i + 4000])

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, _, token = query.data.partition(":")
    item = pending.pop(token, None)

    if not item:
        await query.edit_message_text("⏱ این درخواست منقضی شده، دوباره فایل رو بفرست.")
        return

    chat_id = query.message.chat_id

    if action == "plain":
        try:
            if item["kind"] == "audio":
                await context.bot.send_audio(chat_id=chat_id, audio=item["file_id"])
            elif item["kind"] == "voice":
                await context.bot.send_voice(chat_id=chat_id, voice=item["file_id"])
            else:
                await context.bot.send_document(chat_id=chat_id, document=item["file_id"])
            await query.edit_message_text("✅ بدون کپشن فرستاده شد.")
        except Exception as e:
            await query.edit_message_text(f"❌ نشد بفرستم: {e}")
        return

    if item["size"] and item["size"] > MAX_TG_FILE:
        await query.edit_message_text("⚠️ فایل بزرگ‌تر از ۲۰ مگابایته و تلگرام اجازه نمی‌ده بات دانلودش کنه.")
        return

    await query.edit_message_text("⏳ دارم به متن تبدیل می‌کنم...")
    await transcribe_and_reply(context, chat_id, item["file_id"], item["filename"], query.message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_counter
    msg = update.message
    if not msg:
        return

    doc = msg.document

    # ویدیو: همیشه مستقیم به متن تبدیل می‌شه
    video = msg.video or msg.video_note
    if not video and doc and (doc.mime_type or "").startswith("video/"):
        video = doc
    if video:
        if video.file_size and video.file_size > MAX_TG_FILE:
            await msg.reply_text("⚠️ فایل بزرگ‌تر از ۲۰ مگابایته و تلگرام اجازه نمی‌ده بات دانلودش کنه.")
            return
        status = await msg.reply_text("⏳ دارم به متن تبدیل می‌کنم...")
        filename = getattr(video, "file_name", None) or "video.mp4"
        await transcribe_and_reply(context, msg.chat_id, video.file_id, filename, status)
        return

    # آهنگ یا ویس: می‌پرسه چیکار کنم
    kind = None
    media = None
    filename = None
    if msg.audio:
        kind, media = "audio", msg.audio
        filename = msg.audio.file_name or "audio.mp3"
    elif msg.voice:
        kind, media = "voice", msg.voice
        filename = "voice.ogg"
    elif doc and (doc.mime_type or "").startswith("audio/"):
        kind, media = "document", doc
        filename = doc.file_name or "audio.mp3"

    if not media:
        await msg.reply_text("آهنگ، ویس یا ویدیو بفرست تا کارش رو انجام بدم.")
        return

    if len(pending) > 200:
        pending.pop(next(iter(pending)))

    pending_counter += 1
    token = str(pending_counter)
    pending[token] = {
        "kind": kind,
        "file_id": media.file_id,
        "filename": filename,
        "size": media.file_size,
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📝 استخراج متن", callback_data=f"text:{token}"),
        InlineKeyboardButton("🎵 بدون کپشن", callback_data=f"plain:{token}"),
    ]])
    await msg.reply_text("متنش رو استخراج کنم یا بدون کپشن برات بفرستم؟", reply_markup=keyboard)

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_choice))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
