import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))

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
    msg = update.message

    origin = getattr(msg, "forward_origin", None)
    origin_chat = getattr(origin, "chat", None)
    if origin_chat:
        await msg.reply_text(f"آی‌دی کانال مبدا: {origin_chat.id}")

    file_id = msg.audio.file_id if msg.audio else (msg.document.file_id if msg.document else None)

    if file_id:
        try:
            await context.bot.send_audio(chat_id=TARGET_CHANNEL_ID, audio=file_id)
            await msg.reply_text("✅ اهنگ فرستاده شد!")
        except Exception as e:
            await msg.reply_text(f"❌ نشد بفرستم: {e}")
    elif not origin_chat:
        await msg.reply_text(f"آی‌دی این چت: {update.effective_chat.id}")

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
