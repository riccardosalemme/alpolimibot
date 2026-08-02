from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message

from db import log_activity
from locales import t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, lang: str):
    log_activity("start")
    await message.answer(t(lang, "welcome", name=html.bold(message.from_user.first_name)))
