from enum import Enum
from aiogram.fsm.state import State, StatesGroup

class UserStatus(str, Enum):
    UNKNOWN = "unknown"
    ANONYMOUS = "anonymous"
    AUTHORIZED = "authorized"

class TestProcess(StatesGroup):
    """Состояния прохождения теста"""
    in_attempt = State()