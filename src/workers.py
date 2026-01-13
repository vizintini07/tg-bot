import asyncio
import logging
from aiogram import Bot
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
                
                # Опрашиваем /auth/status
                resp, status = await api.check_login_status(token)
                
                # В Go: если Status == "granted", значит токены выданы 
                if status == 200 and resp and resp.get("status") == "granted":
                    await sm.set_authorized(
                        chat_id, 
                        access_token=resp.get("access_token"), 
                        refresh_token=resp.get("refresh_token")
                    )
                    await bot.send_message(chat_id, "✅ Авторизация успешна! Доступ к тестам открыт.")
                
                # Если 404 или токен протух в Go (cleanOldData удаляет их [cite: 7])
                elif status == 404 or resp.get("status") == "not_found":
                    await sm.logout(chat_id)
                    # Не спамим, если сессия просто исчезла
        except Exception as e:
            logging.error(f"Polling Error: {e}")
        
        await asyncio.sleep(5)