from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.states import TestProcess
from src.services.api import BackendClient
from src.services.storage import UserSessionManager

router = Router()

@router.callback_query(F.data.startswith("start_test:"))
async def start_attempt(callback: types.CallbackQuery, state: FSMContext, session_manager: UserSessionManager, api: BackendClient):
    test_id = callback.data.split(":")[1]
    session = await session_manager.get_session(callback.message.chat.id)
    
    attempt, code = await api.create_attempt(session['access_token'], test_id)
    
    if code != 200:
        await callback.answer("Не удалось начать тест", show_alert=True)
        return

    # Сохраняем состояние теста в FSM
    await state.update_data(
        attempt_id=attempt['id'],
        question_ids=attempt['questions'], # список ID вопросов
        current_index=0,
        access_token=session['access_token']
    )
    await state.set_state(TestProcess.in_attempt)
    await render_question(callback.message, state, api)

async def render_question(message: types.Message, state: FSMContext, api: BackendClient):
    data = await state.get_data()
    q_ids = data['question_ids']
    idx = data['current_index']
    
    if idx >= len(q_ids):
        await finish_ui(message, state, api)
        return

    q_id = q_ids[idx]
    token = data['access_token']
    
    # Параллельно: данные вопроса и текущий ответ
    q_data, _ = await api.get_question_details(token, q_id)
    ans_data, _ = await api.get_answer(token, data['attempt_id'], q_id)
    
    cur_ans = ans_data.get('answer_index', -1) if ans_data else -1
    
    text = f"❓ <b>Вопрос {idx+1}/{len(q_ids)}</b>\n\n{q_data['text']}"
    
    kb = InlineKeyboardBuilder()
    for i, option in enumerate(q_data['options']):
        marker = "✅" if i == cur_ans else ""
        kb.button(text=f"{marker} {option}", callback_data=f"ans:{i}")
    
    # Навигация
    nav_buttons = []
    if idx > 0: nav_buttons.append(types.InlineKeyboardButton(text="⬅️", callback_data="nav:prev"))
    nav_buttons.append(types.InlineKeyboardButton(text="⏹ Завершить", callback_data="finish_attempt"))
    if idx < len(q_ids) - 1: nav_buttons.append(types.InlineKeyboardButton(text="➡️", callback_data="nav:next"))
    
    kb.row(*nav_buttons)
    
    await message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(TestProcess.in_attempt, F.data.startswith("ans:"))
async def save_answer(callback: types.CallbackQuery, state: FSMContext, api: BackendClient):
    ans_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    q_id = data['question_ids'][data['current_index']]
    
    await api.submit_answer(data['access_token'], data['attempt_id'], q_id, ans_idx)
    await render_question(callback.message, state, api) # Перерисовка галочки
    await callback.answer()

@router.callback_query(TestProcess.in_attempt, F.data.startswith("nav:"))
async def navigate(callback: types.CallbackQuery, state: FSMContext, api: BackendClient):
    direction = 1 if callback.data == "nav:next" else -1
    data = await state.get_data()
    await state.update_data(current_index=data['current_index'] + direction)
    await render_question(callback.message, state, api)

@router.callback_query(TestProcess.in_attempt, F.data == "finish_attempt")
async def finish_handler(callback: types.CallbackQuery, state: FSMContext, api: BackendClient):
    await finish_ui(callback.message, state, api)

async def finish_ui(message: types.Message, state: FSMContext, api: BackendClient):
    data = await state.get_data()
    res, _ = await api.finish_attempt(data['access_token'], data['attempt_id'])
    await state.clear()
    await message.edit_text(f"🏁 Тест завершен.\nРезультат: {res.get('score', '---')}")