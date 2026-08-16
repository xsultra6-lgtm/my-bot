import os
import asyncio
import subprocess
import static_ffmpeg
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiohttp import web

# FFmpeg-ni sozlash
static_ffmpeg.add_paths()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_languages = {}

# Matnlar to'plami
TEXTS = {
    "description": {
        "uz": "✅ Til o'zgartirildi! \n\nMen nimalar qila olaman? \n🎵 Ovozli xabarlaringizni MP3 formatiga o'tkazib beraman.\n🎤 Menga shunchaki ovozli xabar yuboring, qolganini o'zim bajaraman.",
        "en": "✅ Language changed! \n\nWhat can I do? \n🎵 I convert your voice messages to MP3 format.\n🎤 Just send me a voice message, and I'll do the rest.",
        "ru": "✅ Язык изменен! \n\nЧто я умею? \n🎵 Я конвертирую ваши голосовые сообщения в формат MP3.\n🎤 Просто отправьте мне голосовое сообщение, и я сделаю все остальное."
    },
    "converting": {
        "uz": "⏳ MP3 formatiga o'tkazilmoqda...", 
        "en": "⏳ Converting to MP3...", 
        "ru": "⏳ Конвертация в MP3..."
    }
}

def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Salom! Tilni tanlang / Hi! Select a language:", reply_markup=get_language_keyboard())

@dp.callback_query(F.data.startswith("lang_"))
async def process_language_choice(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_languages[callback.from_user.id] = lang_code
    
    # Endi "Til o'zgartirildi" o'rniga tushuntirish xabarini yuboramiz
    description_text = TEXTS["description"].get(lang_code, "Language changed!")
    await callback.message.edit_text(description_text)
    await callback.answer()

@dp.message(F.voice | F.audio)
async def process_audio(message: types.Message):
    lang = user_languages.get(message.from_user.id, "uz")
    status_msg = await message.answer(TEXTS["converting"].get(lang, "Converting..."))
    
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file_info = await bot.get_file(file_id)
    
    ogg_path = f"voice_{message.message_id}.ogg"
    mp3_path = f"audio_{message.message_id}.mp3"
    
    await bot.download_file(file_info.file_path, ogg_path)
    
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", ogg_path, 
            "-vn", "-acodec", "libmp3lame", 
            "-q:a", "2", mp3_path
        ], check=True)
        
        audio_file = FSInputFile(mp3_path)
        await message.answer_audio(audio=audio_file, caption="🎵 Tayyor!")
    except Exception as e:
        await message.answer(f"Xatolik: {e}")
    
    await status_msg.delete()
    if os.path.exists(ogg_path): os.remove(ogg_path)
    if os.path.exists(mp3_path): os.remove(mp3_path)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

