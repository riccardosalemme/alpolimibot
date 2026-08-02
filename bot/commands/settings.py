from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from callbacks import SettingsCB
from db import db_save_preference, db_sedi_visibili, log_activity
from locales import DEFAULT_LANG, SUPPORTED_LANGUAGES, lang_display_name, t
from states import Settings

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message, lang: str, pref: Optional[dict]):
    info = ""
    if pref and pref.get("language"):
        info += t(lang, "settings_current_language",
                  language_name=lang_display_name(pref["language"]))
    if pref and pref.get("sede_name"):
        info += t(lang, "settings_current_sede", sede=pref["sede_name"])
    if info:
        info += "\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(lang, "settings_action_language"),
            callback_data=SettingsCB(campo="lang").pack(),
        ),
        InlineKeyboardButton(
            text=t(lang, "settings_action_sede"),
            callback_data=SettingsCB(campo="sede").pack(),
        ),
    ]])
    await message.answer(f"{info}{t(lang, 'settings_choose_action')}", reply_markup=kb)


@router.callback_query(SettingsCB.filter(F.campo == "lang"))
async def on_sett_lang(callback: CallbackQuery, state: FSMContext, lang: str):
    langs_map = {label: code for code, label in SUPPORTED_LANGUAGES.items()}
    await state.set_state(Settings.waiting_for_language)
    await state.update_data(langs_map=langs_map, current_lang=lang)
    await callback.message.answer(
        t(lang, "settings_choose_language"),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=label) for label in SUPPORTED_LANGUAGES.values()]],
            resize_keyboard=True,
        ),
    )
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.campo == "sede"))
async def on_sett_sede(
    callback: CallbackQuery, state: FSMContext, lang: str, pref: Optional[dict]
):
    sedi = db_sedi_visibili()
    if not sedi:
        return await callback.answer(t(lang, "settings_no_sedi"), show_alert=True)

    sedi_map = {s["nome"]: s["csis"] for s in sedi}
    await state.set_state(Settings.waiting_for_sede)
    await state.update_data(sedi_map=sedi_map, current_lang=lang)

    nomi = list(sedi_map)
    kb_buttons = [[KeyboardButton(text=n) for n in nomi[i:i + 2]] for i in range(0, len(nomi), 2)]
    intro = (
        t(lang, "settings_current_sede", sede=pref["sede_name"]) + "\n"
        if pref and pref.get("sede_name") else ""
    )
    await callback.message.answer(
        f"{intro}{t(lang, 'settings_choose_sede')}",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True),
    )
    await callback.answer()


# ── Uscita dagli stati ───────────────────────────────────────────
# Senza questi due handler ogni messaggio successivo finirebbe nel catch-all di
# stato: chi apre /settings e poi digita un comando resterebbe bloccato, perché
# i filtri di stato hanno la precedenza sui filtri Command.

@router.message(Settings.waiting_for_language, F.text.startswith("/"))
@router.message(Settings.waiting_for_sede, F.text.startswith("/"))
async def settings_annullato(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(t(lang, "settings_cancelled"), reply_markup=ReplyKeyboardRemove())


# ── Salvataggio ──────────────────────────────────────────────────

@router.message(Settings.waiting_for_language)
async def save_language(message: Message, state: FSMContext, pref: Optional[dict]):
    data = await state.get_data()
    langs_map = data.get("langs_map", {})
    current_lang = data.get("current_lang", DEFAULT_LANG)
    chosen_label = message.text.strip()

    if chosen_label not in langs_map:
        return await message.answer(t(current_lang, "settings_invalid_language"))

    lang = langs_map[chosen_label]
    # None e non "": la sede non ancora scelta resta NULL a database.
    db_save_preference(
        message.from_user.id,
        pref.get("sede_name") if pref else None,
        pref.get("sede_csis") if pref else None,
        language=lang,
    )
    log_activity("settings_language", language=lang)
    await state.clear()
    await message.answer(
        t(lang, "settings_saved_language", lang_name=lang_display_name(lang)),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Settings.waiting_for_sede)
async def save_sede(message: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    sedi_map = data.get("sedi_map", {})
    current_lang = data.get("current_lang", DEFAULT_LANG)
    nome_sede = message.text.strip()

    if nome_sede not in sedi_map:
        return await message.answer(t(current_lang, "settings_invalid_sede"))

    db_save_preference(message.from_user.id, nome_sede, sedi_map[nome_sede], language=lang)
    log_activity("settings_sede", sede_csis=sedi_map[nome_sede])
    await state.clear()
    await message.answer(
        t(lang, "settings_saved_sede", sede=nome_sede),
        reply_markup=ReplyKeyboardRemove(),
    )
