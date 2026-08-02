from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from db import db_save_report, log_activity
from locales import t
from states import ReportState

router = Router()


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext, lang: str):
    await state.set_state(ReportState.waiting_for_message)
    await message.answer(t(lang, "report_prompt"), reply_markup=ReplyKeyboardRemove())


@router.message(ReportState.waiting_for_message, F.text.startswith("/"))
async def report_annullato(message: Message, state: FSMContext, lang: str):
    """Un comando digitato durante la segnalazione la annulla invece di finire nel testo."""
    await state.clear()
    await message.answer(t(lang, "report_cancelled"))


@router.message(ReportState.waiting_for_message)
async def process_report(message: Message, state: FSMContext, lang: str):
    db_save_report(message.text)
    log_activity("report")
    await state.clear()
    await message.answer(t(lang, "report_saved"))
