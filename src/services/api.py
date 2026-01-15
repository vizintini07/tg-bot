import aiohttp
import json
from src.config import settings

class BackendClient:
    # Базовый метод для запросов к Main Module
    async def _request(self, method: str, url: str, token: str = None, json_data: dict = None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=json_data, headers=headers) as resp:
                return await resp.json(), resp.status

    async def request_auth_url(self, provider: str, login_token: str):
        url = f"{settings.AUTH_SERVICE_URL}/auth/request"
        form_data = aiohttp.FormData()
        form_data.add_field('provider', provider)
        form_data.add_field('login_token', login_token)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as resp:
                try:
                    return await resp.json(), resp.status
                except:
                    return {}, resp.status

    async def check_login_status(self, login_token: str):
        url = f"{settings.AUTH_SERVICE_URL}/auth/status?state={login_token}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                try:
                    return await resp.json(), resp.status
                except:
                    return {}, resp.status

    
    async def verify_auth_code(self, code: str, login_token: str):
        """Отправка введенного вручную кода на проверку"""
        url = f"{settings.AUTH_SERVICE_URL}/auth/verify"
        payload = {
            "code": code,
            "login_token": login_token
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                try:
                    return await resp.json(), resp.status
                except:
                    return {}, resp.status