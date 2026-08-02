"""
states.py – FSM state groups condivisi tra i comandi.
"""

from aiogram.fsm.state import State, StatesGroup


class Settings(StatesGroup):
    waiting_for_language = State()
    waiting_for_sede = State()


class ReportState(StatesGroup):
    waiting_for_message = State()