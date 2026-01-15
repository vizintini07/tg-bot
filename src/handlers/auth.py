import uuid
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.services.api import BackendClient
from src.config import settings
from src.states import UserStatus, AuthStates
from src.services.storage import UserSessionManager

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session_manager: UserSessionManager):
    chat_id = message.chat.id
    session = await session_manager.get_session(chat_id)
    
    if session.get('status') == UserStatus.AUTHORIZED:
        await message.answer("Вы уже авторизованы. Используйте /menu для доступа к курсам.")
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="GitHub", callback_data="login:github")
        kb.button(text="Yandex", callback_data="login:yandex")
        kb.button(text="Получить код", callback_data="login:code")
        # Новая кнопка
        kb.button(text="Ввести код из ЛК", callback_data="login:input_code")
        kb.adjust(1)
        await message.answer("Добро пожаловать! Выберите способ входа:", reply_markup=kb.as_markup())

@router.callback_query(F.data == "login:input_code")
async def ask_for_code(callback: types.CallbackQuery, state: FSMContext):
    """Переход в режим ожидания ввода кода"""
    await callback.message.answer("Пожалуйста, введите код, полученный в веб-клиенте:")
    await state.set_state(AuthStates.waiting_for_code)
    await callback.answer()

@router.message(AuthStates.waiting_for_code)
async def process_manual_code(message: types.Message, state: FSMContext, 
                              api: BackendClient, session_manager: UserSessionManager):
    """Обработка текстового сообщения с кодом"""
    user_code = message.text.strip()
    login_token = str(uuid.uuid4())
    
    # Отправляем на проверку в Go
    data, status = await api.verify_auth_code(user_code, login_token)
    
    if status == 200 and data.get("status") == "granted":
        await session_manager.set_authorized(
            message.chat.id,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token")
        )
        await message.answer("✅ Авторизация успешна! Теперь вам доступно /menu.")
        await state.clear()
    else:
        await message.answer("❌ Код неверный или устарел. Попробуйте еще раз или выберите другой метод входа (/start).")

@router.callback_query(F.data.startswith("login:"))
async def process_login(callback: types.CallbackQuery, session_manager: UserSessionManager, api: BackendClient):
    """Обработка стандартных методов (GitHub, Yandex, Получить код)"""
    auth_type = callback.data.split(":")[1]
    
    # Игнорируем input_code здесь, так как для него отдельный хендлер выше
    if auth_type == "input_code":
        return

    login_token = str(uuid.uuid4())
    await session_manager.set_anonymous(callback.message.chat.id, login_token)
    
    data, status = await api.request_auth_url(auth_type, login_token)
    
    if status != 200:
        await callback.answer("Ошибка связи с сервером", show_alert=True)
        return

    if auth_type == "code":
        auth_code = data.get("code") 
        await callback.message.edit_text(
            f"Ваш код для входа: <code>{auth_code}</code>\n\n"
            f"Введите этот код в веб-интерфейсе для авторизации."
        )
    else:
        url = data.get("url")
        await callback.message.edit_text(
            f"Для входа через {auth_type.capitalize()} перейдите по ссылке:\n{url}",
            disable_web_page_preview=True
        )
    await callback.answer()