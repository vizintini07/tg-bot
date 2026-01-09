import aiohttp
from src.config import settings
import json

class BackendClient:
    # Базовый метод для запросов к Main Module
    async def _request(self, method: str, url: str, token: str = None, json_data: dict = None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=json_data, headers=headers) as resp:
                return await resp.json(), resp.status

    #НОВАЯ СЕКЦИЯ ДЛЯ GO-СЕРВЕРА
    async def request_auth_url(self, provider: str, login_token: str):
        """
        Go сервер ожидает POST с FORM-DATA!
        """
        url = f"{settings.AUTH_SERVICE_URL}/auth/request"
        
        form_data = aiohttp.FormData()
        form_data.add_field('provider', provider)
        form_data.add_field('login_token', login_token)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as resp:
                try:
                    return await resp.json(), resp.status
                except aiohttp.ContentTypeError:
                    text = await resp.text()
                    return json.loads(text), resp.status

    async def check_login_status(self, login_token: str):
        url = f"{settings.AUTH_SERVICE_URL}/auth/status?state={login_token}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                try:
                    return await resp.json(), resp.status
                except aiohttp.ContentTypeError:
                    text = await resp.text()
                    return json.loads(text), resp.status
