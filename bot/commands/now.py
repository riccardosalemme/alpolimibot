from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from cache import aule_cache, slim_aula
from callbacks import PageCB
from config import TZ
from db import db_aule_libere, log_activity
from formatters import fmt_giorno
from keyboards import aule_keyboard
from locales import DEFAULT_LANG, t

router = Router()


@router.message(Command("now"))
async def cmd_now(message: Message, lang: str, pref: Optional[dict]):
    if not pref or not pref.get("sede_csis"):
        return await message.answer(t(lang, "now_no_settings"))

    now = datetime.now(TZ).replace(second=0, microsecond=0, tzinfo=None)
    fine = now + timedelta(hours=1)
    fascia = f"{now.strftime('%H:%M')} – {fine.strftime('%H:%M')}"

    log_activity("now", sede_csis=pref["sede_csis"], giorno=now.date(),
                 ora_inizio=now.time(), ora_fine=fine.time())
    msg = await message.answer(t(lang, "now_searching"))
    aule = db_aule_libere(pref["sede_csis"], now, fine, message.from_user.id)

    if not aule:
        return await msg.edit_text(t(lang, "now_no_aule"))

    # giorno=None: /now non mostra l'intestazione con la data, /search sì.
    aule_cache[msg.message_id] = {
        "aule": [slim_aula(a) for a in aule],
        "fascia": fascia,
        "lang": lang,
        "giorno": None,
    }
    testo, kb = aule_keyboard(aule, 0, fascia, lang)
    try:
        await msg.edit_text(testo, reply_markup=kb)
    except TelegramBadRequest:
        pass


@router.callback_query(PageCB.filter())
async def pagina_aule(callback: CallbackQuery, callback_data: PageCB, lang: str):
    """Paginazione condivisa da /now, /search e /fav: lo stato sta tutto in cache."""
    cached = aule_cache.get(callback.message.message_id)
    if not cached:
        return await callback.answer(t(lang, "page_expired"), show_alert=True)

    # La lingua della lista è quella con cui è stata generata: cambiarla a metà
    # paginazione mescolerebbe due lingue nello stesso messaggio.
    lang = cached.get("lang", DEFAULT_LANG)
    testo, kb = aule_keyboard(
        cached["aule"], callback_data.page, cached["fascia"], lang,
        cached.get("header_key", "aule_libere_header"),
    )
    # Le liste di /search hanno l'intestazione con la data: va riprodotta a ogni
    # pagina, altrimenti sparisce al primo click su Succ/Prec.
    if cached.get("giorno"):
        testo = f"📅 {fmt_giorno(cached['giorno'], lang)}\n" + testo
    try:
        await callback.message.edit_text(testo, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()
