from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from locales import t

router = Router()


@router.message(Command("about"))
async def cmd_about(message: Message, lang: str):
    await message.answer(t(lang, "about"), disable_web_page_preview=True)
