from pyrogram import Client, filters, types
import yt_dlp
import tempfile
import os

# ===== CONFIG =====
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

app = Client(
    "yt_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TELEGRAM_TOKEN
)

user_context = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 Hey it's *Joss!* \n\n"
        "📥 You want to download a YouTube link? \n"
        "👉 Just *drop it here* — I'll handle the rest! 🚀",
        parse_mode='md'  # ✅ FIXED: 'md' not 'Markdown'
    )

@app.on_message(filters.text)
async def handle_link(client, message):
    if message.text.startswith('/'):
        return
    
    text = message.text.strip()
    if "youtube.com" not in text and "youtu.be" not in text:
        return await message.reply_text("⚠️ Please send a valid YouTube link")
    
    await message.reply_text("🔍 Fetching formats...")
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(text, download=False)
        
        user_context[message.from_user.id] = {'link': text, 'title': info.get('title', 'Video')}
        formats = [
            ('360p', 'bv[height<=360][ext=mp4]'),
            ('480p', 'bv[height<=480][ext=mp4]'),
            ('720p', 'bv[height<=720][ext=mp4]'),
            ('1080p', 'bv[height<=1080][ext=mp4]'),
            ('🎵 Audio (MP3)', 'ba[ext=m4a]')
        ]
        
        keyboard = []
        for i in range(0, len(formats), 2):
            row = [types.InlineKeyboardButton(fmt[0], callback_data=fmt[1]) for fmt in formats[i:i+2]]
            keyboard.append(row)
        
        await message.reply_text(
            f"🎬 *{info['title']}*\n\n🎯 Choose format:",
            parse_mode='md',  # ✅ FIXED: 'md' not 'Markdown'
            reply_markup=types.InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)[:60]}")

@app.on_callback_query()
async def download_format(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_context:
        return await callback_query.answer("⚠️ Send link first!")
    
    fmt_id = callback_query.data
    await callback_query.message.edit_text("⏳ Downloading...")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'format': fmt_id,
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'retries': 10
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(user_context[user_id]['link'], download=True)
                file_path = ydl.prepare_filename(info)
            
            if file_path.endswith('.webm'):
                new_path = file_path.replace('.webm', '.mp4')
                os.rename(file_path, new_path)
                file_path = new_path
            
            if file_path.endswith(('.mp3', '.m4a')):
                await callback_query.message.reply_audio(open(file_path, 'rb'), title=info['title'])
            else:
                await callback_query.message.reply_video(
                    open(file_path, 'rb'),
                    caption=f"✅ {info['title']}",
                    supports_streaming=True
                )
        
        del user_context[user_id]
        await callback_query.message.edit_text("🎉 Done!")
        
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Failed: {str(e)[:80]}")

if __name__ == "__main__":
    app.run()
