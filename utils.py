import asyncio
import logging
import re
import urllib.parse
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

BOT_TOKEN = "8737300376:AAGDEoe8UdjoFaKxQ7zGbaC_F-hOe0xxU-o"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def extract_url(text: str) -> str | None:
    pattern = r"https?://[^\s]+"
    match = re.search(pattern, text)
    return match.group(0) if match else None


async def resolve_url_and_get_coords(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    urls_to_check = [url]
    html_text = ""

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, allow_redirects=True, timeout=12) as resp:
                for history in resp.history:
                    urls_to_check.append(str(history.url))
                    if 'location' in history.headers:
                        urls_to_check.append(history.headers['location'])
                urls_to_check.append(str(resp.url))
                html_text = await resp.text()
    except Exception:
        pass

    # --- 1. SAHIFA ICHIDAN SCHEMA.ORG (JSON-LD) GEOKOORDINATALARINI QIDIRISH (Aynan Yandex/Google Org uchun) ---
    if html_text:
        # Schema.org standard: "latitude": 56.83, "longitude": 60.58
        match = re.search(r'"latitude"\s*:\s*(-?\d+\.\d+)\s*,\s*"longitude"\s*:\s*(-?\d+\.\d+)', html_text)
        if match:
            return float(match.group(1)), float(match.group(2))

        match = re.search(r'"longitude"\s*:\s*(-?\d+\.\d+)\s*,\s*"latitude"\s*:\s*(-?\d+\.\d+)', html_text)
        if match:
            return float(match.group(2)), float(match.group(1))

        # Yandex Static Maps meta tagidan: pt=longitude,latitude
        match = re.search(r'static-maps\.yandex\.[^"\'\s]+\?pt=(-?\d+\.\d+)(?:%2C|,)(-?\d+\.\d+)', html_text)
        if match:
            lon, lat = float(match.group(1)), float(match.group(2))
            return lat, lon

        # Google Maps HTML ichidagi !3d va !4d
        match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", html_text)
        if match:
            return float(match.group(1)), float(match.group(2))

        # Yandex JSON ichidagi coordinates: [lon, lat]
        match = re.search(r'"coordinates"\s*:\s*\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]', html_text)
        if match:
            lon, lat = float(match.group(1)), float(match.group(2))
            return lat, lon

    # --- 2. HAVOLA (URL) TARKIBIDAN QIDIRISH ---
    for u in urls_to_check:
        decoded_u = urllib.parse.unquote(u)

        # Google Maps pinpoint (!3dLAT!4dLON)
        match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", decoded_u)
        if match:
            return float(match.group(1)), float(match.group(2))

        # Yandex point/ll/rtext (pt=LON,LAT)
        match = re.search(r"(?:pt|ll|whatshere%5Bpoint%5D)=(-?\d+\.\d+)(?:%2C|,)(-?\d+\.\d+)", decoded_u)
        if match:
            lon, lat = float(match.group(1)), float(match.group(2))
            return lat, lon

        # Google Maps search / query (?q=LAT,LON)
        match = re.search(r"[?&/](?:q|query|destination)=(-?\d+\.\d+),(-?\d+\.\d+)", decoded_u)
        if match:
            return float(match.group(1)), float(match.group(2))

        # Google Maps place center (@LAT,LON)
        match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", decoded_u)
        if match:
            return float(match.group(1)), float(match.group(2))

    return None, None


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Salom! Menga Google Maps yoki Yandex Maps havolasini yuboring. "
        "Men uni Telegram geolokatsiyasi ko'rinishida qaytarib beraman!"
    )


@dp.message()
async def location_handler(message: types.Message):
    url = extract_url(message.text)

    if not url:
        await message.answer("❌ Matn ichida hech qanday havola topilmadi.")
        return

    wait_msg = await message.answer("🔍 Koordinatalar aniqlanmoqda...")

    lat, lon = await resolve_url_and_get_coords(url)

    await wait_msg.delete()

    if lat and lon:
        await message.answer_location(latitude=lat, longitude=lon)
    else:
        await message.answer(
            "❌ Kechirasiz, ushbu havoladan koordinatalarni aniqlab bo'lmadi."
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
