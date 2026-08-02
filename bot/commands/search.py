from datetime import date, datetime, timedelta
from typing import Optional

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from cache import aule_cache, slim_aula
from callbacks import SearchBackCB, SearchDurataCB, SearchGiornoCB, SearchOraCB
from db import db_aule_libere, log_activity
from formatters import fmt_giorno
from keyboards import (
    aule_keyboard,
    search_durata_kb,
    search_giorni_kb,
    search_nuova_kb,
    search_ore_kb,
)
from locales import t

router = Router()


def _intro(lang: str) -> str:
    return f"{t(lang, 'search_title')}\n\n{t(lang, 'search_choose_day')}"


@router.message(Command("search"))
async def cmd_search(message: Message, lang: str, pref: Optional[dict]):
    if not pref or not pref.get("sede_csis"):
        return await message.answer(t(lang, "now_no_settings"))
    await message.answer(_intro(lang), reply_markup=search_giorni_kb(lang))


@router.callback_query(SearchBackCB.filter())
async def search_back(callback: CallbackQuery, lang: str):
    try:
        await callback.message.edit_text(_intro(lang), reply_markup=search_giorni_kb(lang))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(SearchGiornoCB.filter())
async def search_scegli_ora(callback: CallbackQuery, callback_data: SearchGiornoCB, lang: str):
    giorno = date.fromisoformat(callback_data.giorno)
    try:
        await callback.message.edit_text(
            f"{t(lang, 'search_title')}\n"
            f"📅 {fmt_giorno(giorno, lang)}\n\n"
            f"{t(lang, 'search_choose_hour')}",
            reply_markup=search_ore_kb(giorno, lang),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(SearchOraCB.filter())
async def search_scegli_durata(callback: CallbackQuery, callback_data: SearchOraCB, lang: str):
    giorno = date.fromisoformat(callback_data.giorno)
    try:
        await callback.message.edit_text(
            f"{t(lang, 'search_title')}\n"
            f"📅 {fmt_giorno(giorno, lang)} – 🕐 {callback_data.ora:02d}:00\n\n"
            f"{t(lang, 'search_choose_duration')}",
            reply_markup=search_durata_kb(giorno, callback_data.ora, lang),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(SearchDurataCB.filter())
async def search_risultati(
    callback: CallbackQuery, callback_data: SearchDurataCB, lang: str, pref: Optional[dict]
):
    if not pref or not pref.get("sede_csis"):
        return await callback.answer(t(lang, "now_no_settings"), show_alert=True)

    giorno = date.fromisoformat(callback_data.giorno)
    da = datetime(giorno.year, giorno.month, giorno.day, callback_data.ora, 0)
    a = da + timedelta(hours=callback_data.durata)
    fascia = f"{da.strftime('%H:%M')} – {a.strftime('%H:%M')}"

    log_activity("search", sede_csis=pref["sede_csis"], giorno=giorno,
                 ora_inizio=da.time(), ora_fine=a.time())
    await callback.answer(t(lang, "search_searching"))

    aule = db_aule_libere(pref["sede_csis"], da, a, callback.from_user.id)

    if not aule:
        try:
            await callback.message.edit_text(
                t(lang, "search_no_aule", giorno=fmt_giorno(giorno, lang), fascia=fascia),
                reply_markup=search_nuova_kb(lang),
            )
        except TelegramBadRequest:
            pass
        return

    aule_cache[callback.message.message_id] = {
        "aule": [slim_aula(aula) for aula in aule],
        "fascia": fascia,
        "lang": lang,
        "giorno": giorno,
    }
    testo, kb = aule_keyboard(aule, 0, fascia, lang)
    testo = f"📅 {fmt_giorno(giorno, lang)}\n" + testo
    try:
        await callback.message.edit_text(testo, reply_markup=kb)
    except TelegramBadRequest:
        pass
