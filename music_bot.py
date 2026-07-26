import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فقط اهنگ رو دریافت کن و بفرست"""
    
    if update.message.audio:
        audio = update.message.audio
        
        await context.bot.send_audio(
            chat_id=TARGET_CHANNEL_ID,
            audio=audio.file_id
        )
        
        await update.message.reply_text("✅ اهنگ فرستاده شد!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 🎵\nاهنگ برای من بفرست!")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    
    print("🤖 Bot شروع شد...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
