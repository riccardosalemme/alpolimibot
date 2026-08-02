"""
middlewares.py – Middleware condivisi dal dispatcher.
"""

from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from db import db_get_preference
from locales import DEFAULT_LANG, SUPPORTED_LANGUAGES


def detect_lang(user: Optional[User]) -> str:
    """
    Lingua dichiarata dal client Telegram, se fra quelle supportate.
    Serve solo da default per chi non ha ancora scelto: non viene mai scritta
    a database, così non nascono righe di preferenze per utenti di passaggio.
    """
    if user is None or not user.language_code:
        return DEFAULT_LANG
    base = user.language_code.split("-")[0].lower()
    return base if base in SUPPORTED_LANGUAGES else DEFAULT_LANG


class PreferenceMiddleware(BaseMiddleware):
    """
    Risolve preferenze e lingua una sola volta per update e le passa agli
    handler come argomenti `pref` e `lang`, al posto delle chiamate sparse a
    db_get_preference()/get_user_lang().

    Va registrato come middleware *interno* di dp.update: quelli esterni girano
    prima di UserContextMiddleware, quando event_from_user non esiste ancora.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: Optional[User] = data.get("event_from_user")
        pref = db_get_preference(user.id) if user else None
        data["pref"] = pref
        data["lang"] = (pref or {}).get("language") or detect_lang(user)
        return await handler(event, data)
