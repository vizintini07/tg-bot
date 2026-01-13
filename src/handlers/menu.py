from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.services.storage import UserSessionManager
from src.services.api import BackendClient
from src.states import UserStatus

router = Router()

@router.message(Command("menu"))
@router.callback_query(F.data == "courses")
async def show_courses(event: types.Message | types.CallbackQuery, session_manager: UserSessionManager, api: BackendClient):
    # Универсальный обработчик для команды и кнопки "Назад"
    message = event.message if isinstance(event, types.CallbackQuery) else event
    chat_id = message.chat.id
    
    session = await session_manager.get_session(chat_id)
    if session['status'] != UserStatus.AUTHORIZED:
        await message.answer("Требуется авторизация (/start)")
        return

    data, status = await api.get_courses(session['access_token'])
    if status == 401:
        await message.answer("Сессия истекла. Войдите заново /start")
        return

    kb = InlineKeyboardBuilder()
    if data:
        for course in data:
            kb.button(text=course['title'], callback_data=f"course:{course['id']}")
    kb.adjust(1)
    
    text = "📚 Ваши дисциплины:"
    if isinstance(event, types.CallbackQuery):
        await message.edit_text(text, reply_markup=kb.as_markup())
    else:
        await message.answer(text, reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("course:"))
async def show_tests(callback: types.CallbackQuery, session_manager: UserSessionManager, api: BackendClient):
    course_id = callback.data.split(":")[1]
    session = await session_manager.get_session(callback.message.chat.id)
    
    data, _ = await api.get_course_tests(session['access_token'], course_id)
    
    kb = InlineKeyboardBuilder()
    if data:
        for test in data:
            icon = "🟢" if test.get('is_active') else "🔴"
            cb_data = f"start_test:{test['id']}" if test.get('is_active') else "noop"
            kb.button(text=f"{icon} {test['title']}", callback_data=cb_data)
            
    kb.button(text="🔙 Назад", callback_data="courses")
    kb.adjust(1)
    await callback.message.edit_text("📋 Список тестов:", reply_markup=kb.as_markup())