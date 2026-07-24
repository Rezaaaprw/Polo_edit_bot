from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.audio:
        file = await update.message.audio.get_file()
        file_path = f"temp_{update.message.audio.file_id}.mp3"
        await file.download_to_drive(file_path)
        
        with open(file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=TARGET_CHANNEL_ID,
                audio=audio_file
            )
        
        os.remove(file_path)
        await update.message.reply_text("✅ اهنگ فوروارد شد!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! اهنگ برای من بفرست 🎵")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    print("🤖 Bot شروع شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
