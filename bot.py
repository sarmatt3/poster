from invest_helper_funcs import get_currency, key_rate_today, get_moex
import asyncio, os
from aiogram.client.session.aiohttp import AiohttpSession

import logging
from aiogram.types import FSInputFile
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date
from ai import chat

# --- НАСТРОЙКИ ---
PROXY = os.getenv("PROXY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6251262108  # Ваш Telegram ID (только вы сможете управлять)
CHANNEL_ID = -1003848702995  # ID вашего канала (обязательно с -100)
def generate_message(day = 1):
    keyrate = key_rate_today()
    curr = get_currency(True)
    currency = [f'USD: {curr["USD"]["rate"]}', f'EUR: {curr["EUR"]["rate"]}']
    moex = get_moex()
    ai = chat(f"Что значат для инвестора данные котировки: Ключевая ставка: {keyrate}, {currency}, {moex}. Вывод в трех предложениях")
    message = f"""*{date.today().strftime("%d.%m.%Y")}
Что происходит с рынком

МосБиржа:*

_{moex[0]["SECID"]}: {moex[0]["LASTVALUE"]}₽ ({moex[0]["LASTCHANGE"]}%)
{moex[1]["SECID"]}: {moex[1]["LASTVALUE"]}₽ ({moex[1]["LASTCHANGE"]}%)
{moex[2]["SECID"]}: {moex[2]["LASTVALUE"]}₽ ({moex[2]["LASTCHANGE"]}%)_

*💱Валюта\n*
_💵 {currency[0]}₽
💶 {currency[1]}₽_

*🔑 Ключевая ставка:* _{keyrate[1]}_

*Что это значит для инвестора:*

_{ai}_
"""
    return message
    
# Переменные для хранения текстов (в продакшене лучше использовать БД или JSON-файл)
messages_db = {
    "daily": "Привет! Это ежедневное автоматическое сообщение. ☀️",
    "weekly": "Привет! Это еженедельный дайджест новостей. 🚀"
}

# Инициализация бота и диспетчера

session = AiohttpSession(proxy=PROXY)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN), session=session)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")  # Настройте ваш часовой пояс

# Состояния для смены текста сообщений
class AdminStates(StatesGroup):
    waiting_for_daily = State()
    waiting_for_weekly = State()

# --- ФУНКЦИИ ОТПРАВКИ ПО РАСПИСАНИЮ ---
async def send_daily_message():
    try:
        photo = FSInputFile("day.png")
        await bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=generate_message())
        logging.info("Ежедневное сообщение успешно отправлено.")
    except Exception as e:
        logging.error(f"Ошибка отправки ежедневного сообщения: {e}")

async def send_weekly_message():
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=messages_db["weekly"])
        logging.info("Еженедельное сообщение успешно отправлено.")
    except Exception as e:
        logging.error(f"Ошибка отправки еженедельного сообщения: {e}")

# --- КЛАВИАТУРА УПРАВЛЕНИЯ ---
def get_admin_keyboard():
    buttons = [
        [types.KeyboardButton(text="📝 Изменить ежедневное")],
        [types.KeyboardButton(text="📝 Изменить еженедельное")],
        [types.KeyboardButton(text="📢 Проверить текущие тексты")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- ХЕНДЛЕРЫ УПРАВЛЕНИЯ (ТОЛЬКО ДЛЯ АДМИНА) ---
@dp.message(Command("start"), F.from_user.id == ADMIN_ID)
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в панель управления ботом-публикатором!",
        reply_markup=get_admin_keyboard()
    )

@dp.message(F.text == "📢 Проверить текущие тексты", F.from_user.id == ADMIN_ID)
async def view_messages(message: types.Message):
    text = (
        f"**Текущее ежедневное сообщение:**\n{messages_db['daily']}\n\n"
        f"**Текущее еженедельное сообщение:**\n{messages_db['weekly']}"
    )
    await message.answer(text, parse_mode="Markdown")

# Логика изменения ежедневного сообщения
@dp.message(F.text == "📝 Изменить ежедневное", F.from_user.id == ADMIN_ID)
async def edit_daily(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_daily)
    await message.answer("Введите новый текст для **ежедневного** сообщения (или нажмите /cancel для отмены):")

@dp.message(AdminStates.waiting_for_daily, F.text != "/cancel")
async def save_daily(message: types.Message, state: FSMContext):
    messages_db["daily"] = message.text
    await state.clear()
    await message.answer("✅ Ежедневное сообщение успешно обновлено!", reply_markup=get_admin_keyboard())

# Логика изменения еженедельного сообщения
@dp.message(F.text == "📝 Изменить еженедельное", F.from_user.id == ADMIN_ID)
async def edit_weekly(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_weekly)
    await message.answer("Введите новый текст для **еженедельного** сообщения (или нажмите /cancel для отмены):")

@dp.message(AdminStates.waiting_for_weekly, F.text != "/cancel")
async def save_weekly(message: types.Message, state: FSMContext):
    messages_db["weekly"] = message.text
    await state.clear()
    await message.answer("✅ Еженедельное сообщение успешно обновлено!", reply_markup=get_admin_keyboard())

# Отмена действия
@dp.message(Command("cancel"))
async def cancel_action(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_admin_keyboard())

# --- ЗАПУСК БОТА ---
async def main():
    logging.basicConfig(level=logging.INFO)

    # Настройка расписания (Cron)
    # Ежедневно в 09:00
    scheduler.add_job(send_daily_message, CronTrigger(hour=9, minute=0))
    
    # Раз в неделю по понедельникам в 12:00 (day_of_week: 0-понедельник, 6-воскресенье)
    # scheduler.add_job(send_weekly_message, CronTrigger(day_of_week='mon', hour=12, minute=0))

    # Запуск планировщика
    scheduler.start()

    # Запуск бота в режиме Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    print(generate_message())
    
