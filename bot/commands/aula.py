from datetime import datetime
from typing import Optional

from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from callbacks import AulaInfoCB, AulaWeekCB, FavToggleCB, HideCB
from config import FOTO_DIR, MAX_PREFERITI, TZ
from db import (
    db_cerca_aula,
    db_cerca_aula_by_id,
    db_occupazione_giorno,
    db_occupazione_settimana,
    db_toggle_preferito,
    log_activity,
)
from formatters import format_aula_card, format_aula_settimana
from keyboards import aula_detail_keyboard, hide_keyboard
from locales import t

router = Router()


def _foto_file(idaula: int) -> Optional[FSInputFile]:
    p = FOTO_DIR / f"{idaula}.jpeg"
    return FSInputFile(p) if p.exists() else None


async def _send_aula(message: Message, aula: dict, lang: str) -> None:
    """
    Invia la scheda aula con foto (se disponibile) o solo testo.
    `aula` arriva già con il flag `preferita`, calcolato dalla query.
    """
    idaula = aula["idaula"]
    oggi = datetime.now(TZ).date()
    slots = db_occupazione_giorno(idaula, oggi)
    testo = format_aula_card(aula, slots, oggi, lang)
    kb = aula_detail_keyboard(idaula, aula.get("preferita", False), lang)
    foto = _foto_file(idaula)
    if foto:
        await message.answer_photo(foto, caption=testo, reply_markup=kb)
    else:
        await message.answer(testo, reply_markup=kb, disable_web_page_preview=True)


# ── Ricerca per sigla (testo libero) ────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def cerca_per_sigla(message: Message, state: FSMContext, lang: str):
    if await state.get_state() is not None:
        return

    sigla = message.text.strip()
    log_activity("cerca_aula", sigla=sigla)
    aula = db_cerca_aula(sigla, message.from_user.id)

    if not aula:
        return await message.answer(t(lang, "aula_not_found", sigla=html.quote(sigla)))

    await _send_aula(message, aula, lang)


# ── Callback: aula da lista aule libere ─────────────────────────

@router.callback_query(AulaInfoCB.filter())
async def show_aula_card(callback: CallbackQuery, callback_data: AulaInfoCB, lang: str):
    log_activity("dettaglio_aula", idaula=callback_data.idaula)
    aula = db_cerca_aula_by_id(callback_data.idaula, callback.from_user.id)

    if not aula:
        return await callback.answer(t(lang, "aula_data_error"), show_alert=True)

    await _send_aula(callback.message, aula, lang)
    await callback.answer()


# ── Callback: Occupazione settimana ─────────────────────────────

@router.callback_query(AulaWeekCB.filter())
async def show_week_occupation(callback: CallbackQuery, callback_data: AulaWeekCB, lang: str):
    idaula = callback_data.idaula
    log_activity("occupazione_settimana", idaula=idaula)
    aula = db_cerca_aula_by_id(idaula, callback.from_user.id)

    if not aula:
        return await callback.answer(t(lang, "aula_data_error"), show_alert=True)

    testo = format_aula_settimana(aula, db_occupazione_settimana(idaula), lang)
    await callback.message.answer(testo, reply_markup=hide_keyboard(lang))
    await callback.answer()


# ── Callback: Aggiungi/rimuovi dai preferiti ─────────────────────

@router.callback_query(FavToggleCB.filter())
async def toggle_preferito(callback: CallbackQuery, callback_data: FavToggleCB, lang: str):
    idaula = callback_data.idaula
    preferita, limite = db_toggle_preferito(callback.from_user.id, idaula)

    if limite:
        return await callback.answer(t(lang, "fav_limit", max=MAX_PREFERITI), show_alert=True)

    log_activity("fav_add" if preferita else "fav_remove", idaula=idaula)

    # Aggiorna l'etichetta del bottone senza rimandare la scheda.
    try:
        await callback.message.edit_reply_markup(
            reply_markup=aula_detail_keyboard(idaula, preferita, lang)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(t(lang, "fav_added" if preferita else "fav_removed"))


# ── Callback: Nascondi messaggio ─────────────────────────────────

@router.callback_query(HideCB.filter())
async def hide_message(callback: CallbackQuery, lang: str):
    # Telegram non lascia cancellare messaggi più vecchi di 48 ore: senza
    # questo ramo il pulsante sembrerebbe semplicemente non funzionare.
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        return await callback.answer(t(lang, "hide_failed"), show_alert=True)
    await callback.answer()
