import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import from_url

from src.config import settings
from src.services.storage import UserSessionManager
from src.services.api import BackendClient
from src.handlers import auth, menu, testing
from src.workers import check_anonymous_users

async def main():
    logging.basicConfig(level=logging.INFO)

    # Инициализация инфраструктуры
    redis = from_url(settings.REDIS_URL)
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=RedisStorage(redis=redis))

    # Сервисы
    session_manager = UserSessionManager(redis)
    api_client = BackendClient()

    # Внедрение зависимостей (Dependency Injection) в хендлеры
    # Теперь в каждый хендлер автоматически прилетят session_manager и api
    dp["session_manager"] = session_manager
    dp["api"] = api_client

    # Регистрация роутеров
    dp.include_router(auth.router)
    dp.include_router(menu.router)
    dp.include_router(testing.router)

    # Запуск фоновых задач
    asyncio.create_task(check_anonymous_users(bot, session_manager, api_client))

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis.close()

if __name__ == "__main__":
    asyncio.run(main())