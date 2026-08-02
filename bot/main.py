"""
main.py – Entry point del bot.

Avvio:  uv run bot/main.py
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    CallbackQuery,
    ErrorEvent,
    Message,
)
from dotenv import load_dotenv

load_dotenv()

from commands import get_main_router
from config import COMANDI_MENU
from db import close_pool, init_pool
from locales import DEFAULT_LANG, SUPPORTED_LANGUAGES, t
from middlewares import PreferenceMiddleware

TOKEN = os.environ["BOT_TOKEN"]


async def setup_commands(bot: Bot) -> None:
    """
    Registra il menu "/" di Telegram, una lista per lingua supportata.

    `language_code=None` definisce la lista di default, che vale per tutti i
    client la cui lingua non ha una lista dedicata (compresi quelli in italiano).

    Attenzione: Telegram sceglie la lista in base alla lingua del *client*, non
    alla preferenza salvata nel bot. Chi ha Telegram in italiano ma ha scelto
    English in /settings vede comunque il menu italiano — non è aggirabile senza
    una chiamata API per singolo utente.
    """
    for code in SUPPORTED_LANGUAGES:
        comandi = [
            BotCommand(command=nome, description=t(code, f"cmd_{nome}"))
            for nome in COMANDI_MENU
        ]
        await bot.set_my_commands(
            comandi,
            scope=BotCommandScopeAllPrivateChats(),
            language_code=None if code == DEFAULT_LANG else code,
        )


async def on_error(event: ErrorEvent) -> None:
    """
    Rete di sicurezza: senza questo handler un'eccezione verrebbe solo loggata
    e l'utente resterebbe senza risposta, senza capire perché.
    """
    logging.exception("Errore non gestito: %s", event.exception)

    update = event.update
    lang = DEFAULT_LANG
    try:
        if isinstance(update.message, Message):
            await update.message.answer(t(lang, "generic_error"))
        elif isinstance(update.callback_query, CallbackQuery):
            await update.callback_query.answer(t(lang, "generic_error"), show_alert=True)
    except Exception:
        # Se anche la notifica fallisce non c'è altro da fare: il log basta.
        logging.exception("Impossibile notificare l'errore all'utente.")


async def main():
    init_pool()

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # Interno, non esterno: gli outer girano prima di UserContextMiddleware.
    dp.update.middleware(PreferenceMiddleware())
    dp.include_router(get_main_router())
    dp.errors.register(on_error)

    # Il menu è cosmetico: se Telegram non risponde il bot parte lo stesso.
    try:
        await setup_commands(bot)
    except Exception:
        logging.exception("Registrazione del menu comandi fallita.")

    logging.info("Bot avviato.")

    try:
        await dp.start_polling(bot)
    finally:
        close_pool()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
