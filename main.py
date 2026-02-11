import os
import logging
import tempfile
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Missing TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
user_context = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hey it's *Joss!* \n\n"
        "📥 You want to download a YouTube link? \n"
        "👉 Just *drop it here* — I'll handle the rest! 🚀",
        parse_mode='Markdown'
    )

def handle_link(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if "youtube.com" not in text and "youtu.be" not in text:
        update.message.reply_text("⚠️ Please send a valid YouTube link")
        return
    
    msg = update.message.reply_text("🔍 Fetching formats...")
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(text, download=False)
        
        user_context[user_id] = {'link': text, 'title': info.get('title', 'Video')}
        formats = [
            ('360p', 'bv[height<=360][ext=mp4]'),
            ('480p', 'bv[height<=480][ext=mp4]'),
            ('720p', 'bv[height<=720][ext=mp4]'),
            ('1080p', 'bv[height<=1080][ext=mp4]'),
            ('🎵 Audio (MP3)', 'ba[ext=m4a]')
        ]
        
        keyboard = []
        for i in range(0, len(formats), 2):
            row = [InlineKeyboardButton(fmt[0], callback_data=fmt[1]) for fmt in formats[i:i+2]]
            keyboard.append(row)
        
        msg.edit_text(f"🎬 *{info['title']}*\n\n🎯 Choose format:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        msg.edit_text(f"❌ Error: {str(e)[:60]}")

def download_format(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in user_context:
        query.answer("⚠️ Send link first!")
        return
    
    fmt_id = query.data
    query.message.edit_text("⏳ Starting download...")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d['_percent_str'].strip()
                    speed = d.get('_speed_str', '0').strip()
                    query.message.edit_text(f"⏳ Downloading...\n\n`{percent}` • `{speed}`", parse_mode='Markdown')
            
            ydl_opts = {
                'format': fmt_id,
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
                'quiet': False,
                'no_warnings': True,
                'noplaylist': True,
                'retries': 10,
                'progress_hooks': [progress_hook]
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(user_context[user_id]['link'], download=True)
                file_path = ydl.prepare_filename(info)
            
            # Fix .webm → .mp4
            if file_path.endswith('.webm'):
                new_path = file_path.replace('.webm', '.mp4')
                os.rename(file_path, new_path)
                file_path = new_path
            
            query.message.edit_text("📤 Uploading to Telegram...")
            
            if file_path.endswith(('.mp3', '.m4a')):
                query.message.reply_audio(open(file_path, 'rb'), title=info['title'])
            else:
                try:
                    # Try sending as video (fails if >50MB)
                    query.message.reply_video(open(file_path, 'rb'), caption=f"✅ {info['title']}")
                except:
                    # Fallback to document
                    query.message.reply_document(
                        open(file_path, 'rb'),
                        caption=f"✅ {info['title']} | Size: {os.path.getsize(file_path)//1024//1024} MB",
                        disable_content_type_detection=True
                    )
        
        del user_context[user_id]
        query.message.edit_text("🎉 Done!")
        
    except Exception as e:
        query.message.edit_text(f"❌ Failed: {str(e)[:80]}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_handler(CallbackQueryHandler(download_format))
    logger.info("✅ Bot ready")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == '__main__':
    main()
