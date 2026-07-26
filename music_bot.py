from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فقط اهنگ رو دریافت کن و بفرست"""
    
    if update.message.audio:
        # اهنگ رو دریافت کن
        audio = update.message.audio
        
        # فقط اهنگ رو بفرست (بدون متن)
        await context.bot.send_audio(
            chat_id=TARGET_CHANNEL_ID,
            audio=audio.file_id,
            title=audio.title or "",
            performer=audio.performer or ""
        )
        
        # تایید برای کاربر
        await update.message.reply_text("✅ اهنگ فرستاده شد!")
    
    elif update.message.document:
        # اگه به‌صورت فایل
        doc = update.message.document
        
        await context.bot.send_audio(
            chat_id=TARGET_CHANNEL_ID,
            audio=doc.file_id
        )
        
        await update.message.reply_text("✅ اهنگ فرستاده شد!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 🎵\nاهنگ برای من بفرست، من بدون متن به کانالت می‌فرستم!"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # شروع
    app.add_handler(MessageHandler(filters.COMMAND, start))
    
    # اهنگ‌ها
    app.add_handler(MessageHandler(
        filters.AUDIO | filters.Document.MP3 | filters.Document.AUDIO,
        handle_audio
    ))
    
    print("🤖 Bot شروع شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
