import json
import asyncio
from typing import Dict, Any, List
from redis.asyncio import Redis
from src.states import UserStatus

class UserSessionManager:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_session(self, chat_id: int) -> Dict[str, Any]:
        data = await self.redis.get(str(chat_id))
        if not data:
            return {"status": UserStatus.UNKNOWN}
        return json.loads(data)

    async def set_anonymous(self, chat_id: int, login_token: str):
        data = {
            "status": UserStatus.ANONYMOUS,
            "login_token": login_token,
            "created_at": asyncio.get_event_loop().time()
        }
        await self.redis.set(str(chat_id), json.dumps(data))

    async def set_authorized(self, chat_id: int, access_token: str, refresh_token: str):
        data = {
            "status": UserStatus.AUTHORIZED,
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        await self.redis.set(str(chat_id), json.dumps(data))

    async def logout(self, chat_id: int):
        await self.redis.delete(str(chat_id))

    async def get_all_by_status(self, status: UserStatus) -> List[int]:
        """Поиск ключей по статусу (для воркеров)"""
        keys = await self.redis.keys("*")
        result = []
        for key in keys:
            if b":" in key: continue # Пропускаем ключи FSM aiogram
            val = await self.redis.get(key)
            try:
                data = json.loads(val)
                if data.get("status") == status:
                    result.append(int(key))
            except:
                pass
        return result