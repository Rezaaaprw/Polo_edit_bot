import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, CHANNEL_ID, PORT
from github_db import load_seen_songs, save_seen_songs


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
    HTTPServer(("0.0.0.0", PORT), Health).serve_forever()


def already_seen(key):
    return any(song["key"] == key for song in seen_songs)


async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip().lower()

    if not query:
        await update.message.reply_text("اسم آهنگ رو بعد از /search بنویس.")
        return

    matches = [song["key"] for song in seen_songs if query in song["key"]]

    if not matches:
        await update.message.reply_text("❌ همچین آهنگی تو لیست نیست.")
        return

    lines = []

    for m in matches[:10]:
        title, _, performer = m.partition("|")

        if performer:
            lines.append(f"• {title} - {performer}")
        else:
            lines.append(f"• {title}")

    await update.message.reply_text(
        "✅ اینا رو پیدا کردم:\n" + "\n".join(lines)
    )


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_sha

    query = update.callback_query
    await query.answer()

    action, _, token = query.data.partition(":")

    item = pending.pop(token, None)

    if not item:
        await query.edit_message_text(
            "⏱ این درخواست منقضی شده، دوباره آهنگ رو بفرست."
        )
        return

    if action == "cancel":
        await query.edit_message_text("❌ لغو شد.")
        return

    try:
        await context.bot.send_audio(
            chat_id=CHANNEL_ID,
            audio=item["file_id"],
            caption=item["caption"],
        )

        await query.edit_message_text("✅ آهنگ فرستاده شد!")

    except Exception as e:
        await query.edit_message_text(f"❌ نشد بفرستم:\n{e}")
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
        key = (
            f"{audio.title.strip().lower()}|"
            f"{(audio.performer or '').strip().lower()}"
        )

    if key and already_seen(key):
        await msg.reply_text("⚠️ این آهنگ قبلاً فرستاده شده!")
        return

    caption = None

    if audio and audio.title:
        if audio.performer:
            caption = f"{audio.title} - {audio.performer}"
        else:
            caption = audio.title

    pending_counter += 1

    token = str(pending_counter)

    pending[token] = {
        "file_id": file_id,
        "caption": caption,
        "key": key,
    }

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "✅ بفرست",
                callback_data=f"confirm:{token}"
            ),
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=f"cancel:{token}"
            ),
        ]]
    )

    await msg.reply_text(
        "این آهنگ فرستاده بشه؟",
        reply_markup=keyboard,
    )


def create_app():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("search", search_song))
    app.add_handler(CallbackQueryHandler(handle_confirmation))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    return app


def main():
    threading.Thread(
        target=run_health_server,
        daemon=True,
    ).start()

    app = create_app()

    print("Bot started")

    app.run_polling()


if __name__ == "__main__":
    main()
