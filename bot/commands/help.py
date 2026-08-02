"""
help.py – /help e fallback per i comandi non riconosciuti.

Il router va incluso per ultimo: il fallback intercetta qualsiasi messaggio
che inizia con "/" e non sia già stato gestito da un router precedente.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from db import log_activity
from locales import t

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str):
    log_activity("help")
    await message.answer(t(lang, "help"), disable_web_page_preview=True)


@router.message(F.text.startswith("/"))
async def comando_sconosciuto(message: Message, lang: str):
    log_activity("comando_sconosciuto")
    await message.answer(
        f"{t(lang, 'unknown_command')}\n\n{t(lang, 'help')}",
        disable_web_page_preview=True,
    )
