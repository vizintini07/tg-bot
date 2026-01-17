import asyncio
import logging
from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder # Добавляем импорт
from src.states import UserStatus
from src.services.storage import UserSessionManager
from src.services.api import BackendClient

async def check_anonymous_users(bot: Bot, sm: UserSessionManager, api: BackendClient):
    while True:
        try:
            anon_users = await sm.get_all_by_status(UserStatus.ANONYMOUS)
            for chat_id in anon_users:
                session = await sm.get_session(chat_id)
                token = session.get('login_token')
                
                resp, status = await api.check_login_status(token)
                
                # Проверяем статус, который шлет Go-сервис
                if status == 200 and resp and resp.get("status") == "granted":
                    # 1. Обновляем статус в Redis на "authorized"
                    await sm.set_authorized(
                        chat_id, 
                        access_token=resp.get("access_token"), 
                        refresh_token=resp.get("refresh_token")
                    )
                    
                    # 2. Создаем кнопку "Открыть меню"
                    kb = InlineKeyboardBuilder()
                    kb.button(text="📚 Открыть список тестов", callback_data="courses")
                    
                    # 3. Отправляем сообщение с кнопкой
                    await bot.send_message(
                        chat_id, 
                        "✅ **Авторизация успешна!**\nТеперь вам доступен полный функционал бота.",
                        reply_markup=kb.as_markup(),
                        parse_mode="Markdown"
                    )
                    
                elif status == 404:
                    # Если сессия удалена на сервере авторизации
                    await sm.logout(chat_id)
                    
        except Exception as e:
            logging.error(f"Worker error: {e}")
            
        await asyncio.sleep(5) # Пауза между проверками 3 секунды