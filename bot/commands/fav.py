"""
fav.py – /fav: elenco delle aule preferite dell'utente.

Riusa la tastiera paginata di /now: cambia solo l'intestazione (header_key) e
il fatto che ogni bottone porti il pallino di occupazione.
"""

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from cache import aule_cache, slim_aula
from config import TZ
from db import db_aule_preferite, log_activity
from keyboards import aule_keyboard
from locales import t

router = Router()

_HEADER_KEY = "fav_header"


@router.message(Command("fav"))
async def cmd_fav(message: Message, lang: str):
    log_activity("fav")

    adesso = datetime.now(TZ).replace(second=0, microsecond=0, tzinfo=None)
    aule = db_aule_preferite(message.from_user.id, adesso)

    if not aule:
        return await message.answer(t(lang, "fav_empty"))

    # La fascia non compare nell'intestazione di /fav, ma serve al callback di
    # paginazione, che la trasporta nel callback_data.
    fascia = adesso.strftime("%H:%M")

    testo, kb = aule_keyboard(aule, 0, fascia, lang, _HEADER_KEY)
    msg = await message.answer(testo, reply_markup=kb)

    aule_cache[msg.message_id] = {
        "aule": [slim_aula(a) for a in aule],
        "fascia": fascia,
        "lang": lang,
        "giorno": None,
        "header_key": _HEADER_KEY,
    }
