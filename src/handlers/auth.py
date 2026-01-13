import uuid
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.services.api import BackendClient
from src.config import settings
from src.states import UserStatus
from src.services.storage import UserSessionManager

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session_manager: UserSessionManager):
    chat_id = message.chat.id
    session = await session_manager.get_session(chat_id)
    
    if session['status'] == UserStatus.AUTHORIZED:
        await message.answer("Вы уже авторизованы. /menu для доступа к курсам.")
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="GitHub", callback_data="login:github")
        kb.button(text="Yandex", callback_data="login:yandex")
        kb.button(text="Код", callback_data="login:code")
        kb.adjust(1)
        await message.answer("Добро пожаловать! Выберите способ входа:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("login:"))
async def process_login(callback: types.CallbackQuery, session_manager: UserSessionManager, api: BackendClient):
    auth_type = callback.data.split(":")[1]
    login_token = str(uuid.uuid4())
    
    # 1. Сначала регистрируем анонима в Redis
    await session_manager.set_anonymous(callback.message.chat.id, login_token)
    
    # 2. Запрашиваем данные у Go-сервера
    data, status = await api.request_auth_url(auth_type, login_token)
    
    if status != 200 or not data:
        await callback.answer("Ошибка связи с сервером авторизации", show_alert=True)
        return

    if auth_type == "code":
        auth_code = data.get("code") 
        await callback.message.edit_text(f"🔑 Ваш код для входа: `{auth_code}`\nВведите его на сайте.")
    else:
        # Для GitHub/Yandex сервер возвращает {"auth_url": "..."}
        url = data.get("auth_url")
        await callback.message.edit_text(f"🔗 Перейдите по ссылке для входа:\n{url}")
    
    await callback.answer()