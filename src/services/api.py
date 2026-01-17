import aiohttp
import logging
from src.config import settings

class BackendClient:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def _request(self, method: str, url: str, token: str = None, json_data: dict = None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Для C++ и Nginx лучше явно указывать тип контента, если шлем JSON
        if json_data:
            headers["Content-Type"] = "application/json"

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=json_data, headers=headers) as resp:
                # Мы пытаемся прочитать JSON. Если сервер (например C++ или Nginx)
                # вернет ошибку в HTML или пустой ответ, бот не должен упасть.
                try:
                    return await resp.json(), resp.status
                except Exception:
                    # Если пришел не JSON (например, 200 OK но пустое тело, или 502 Bad Gateway)
                    text = await resp.text()
                    return {"text": text}, resp.status
                
    
    async def request_auth_url(self, provider: str, login_token: str):
        url = f"{settings.AUTH_SERVICE_URL}/auth/request"
        payload = {
            "provider": provider,
            "login_token": login_token
    }
    
        async with aiohttp.ClientSession() as session:
        # Отправляем POST запрос
            async with session.post(url, data=payload) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        # ВАЖНО: возвращаем весь словарь данных и статус
                        return data, resp.status
                    except Exception:
                        # Если Go прислал текст вместо JSON
                        text = await resp.text()
                        return {"error": text}, resp.status
                return None, resp.status

    async def check_login_status(self, login_token: str):
        """Проверка статуса токена (Polling воркера)"""
        url = f"{settings.AUTH_SERVICE_URL}/auth/status?state={login_token}"
        # Здесь используем _request, так как это простой GET
        return await self._request("GET", url)

    async def verify_auth_code(self, code: str, login_token: str):
        """
        Проверка введенного вручную кода
        Шлет JSON, так как мы договорились добавить /auth/verify в Go.
        """
        url = f"{settings.AUTH_SERVICE_URL}/auth/verify"
        payload = {
            "code": code,
            "login_token": login_token
        }
        return await self._request("POST", url, json_data=payload)

    # =========================================================
    # ЗОНА MAIN MODULE (C++ СЕРВЕР)
    # =========================================================

    async def get_courses(self, token: str):
        """GET /courses — Список доступных курсов"""
        url = f"{settings.MAIN_MODULE_URL}/courses"
        return await self._request("GET", url, token=token)

    async def get_course_tests(self, token: str, course_id: str):
        """GET /courses/{course_id}/tests — Список тестов курса"""
        url = f"{settings.MAIN_MODULE_URL}/courses/{course_id}/tests"
        return await self._request("GET", url, token=token)

    async def create_attempt(self, token: str, test_id: str):
        """POST /tests/{test_id}/attempts — Начать выполнение теста"""
        url = f"{settings.MAIN_MODULE_URL}/tests/{test_id}/attempts"
        return await self._request("POST", url, token=token)

    async def get_question_details(self, token: str, attempt_id: str, question_id: str):
        """
        GET /attempts/{attempt_id}/questions/{question_id}
        """
        url = f"{settings.MAIN_MODULE_URL}/attempts/{attempt_id}/questions/{question_id}"
        return await self._request("GET", url, token=token)

    async def submit_answer(self, token: str, attempt_id: str, question_id: str, answer_index: int):
        """
        POST /attempts/{attempt_id}/answers
        Тело запроса: {"question_id": "...", "answer_index": 0}
        """
        url = f"{settings.MAIN_MODULE_URL}/attempts/{attempt_id}/answers"
        payload = {
            "question_id": question_id,
            "answer_index": answer_index
        }
        return await self._request("POST", url, token=token, json_data=payload)

    async def finish_attempt(self, token: str, attempt_id: str):
        """
        POST /attempts/{attempt_id}/finish
        Завершает тест и возвращает результат (оценку)
        """
        url = f"{settings.MAIN_MODULE_URL}/attempts/{attempt_id}/finish"
        return await self._request("POST", url, token=token)