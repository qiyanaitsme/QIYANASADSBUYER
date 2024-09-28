import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from handlers import register_handlers, init_db
import asyncio

API_TOKEN = 'ВАШ ТОКЕН БОТА'
ADMIN_IDS = [ЦИФРЫ ID]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

async def on_startup(dp):
    await init_db()

register_handlers(dp, ADMIN_IDS)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
