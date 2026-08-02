"""
userinfo.py – /userinfo: mostra tutti i dati che Telegram espone sull'utente
e, per contrasto, i pochi dati che il bot memorizza davvero.

Testi volutamente hardcoded in inglese: comando diagnostico, fuori da locales.json.
"""

import json
import logging

from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from config import MAX_PREFERITI, TZ, USERINFO_MAX_VALUE_LEN
from db import db_preferiti_ids, db_user_stored_data, log_activity

router = Router()

_STORED_NOTE = (
    "<blockquote>Everything above this section is what Telegram exposes to the bot "
    "on every message: <b>none of it is stored</b>.\n"
    "Usage statistics are anonymous (no identifier attached) and /report submissions "
    "contain only the text and the date.</blockquote>"
)


def _fmt_value(value: object) -> str:
    """Scalari come sono, strutture annidate come JSON compatto su una riga."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    else:
        value = str(value)
    if len(value) > USERINFO_MAX_VALUE_LEN:
        value = value[:USERINFO_MAX_VALUE_LEN] + "…"
    return value


def _fmt_block(data: dict) -> str:
    """Blocco <pre> con una riga per campo. Stringa vuota se non c'è nulla."""
    if not data:
        return ""
    righe = "\n".join(f"{k}: {_fmt_value(v)}" for k, v in sorted(data.items()))
    return f"<pre>{html.quote(righe)}</pre>"


@router.message(Command("userinfo"))
async def cmd_userinfo(message: Message):
    log_activity("userinfo")

    user = message.from_user
    sezioni: list[str] = [f"🪪 {html.bold('Your data')}"]

    # ── 1. Dati utente grezzi ────────────────────────────────────
    sezioni.append(f"\n👤 {html.bold('User data (Telegram)')}")
    sezioni.append(_fmt_block(user.model_dump(exclude_none=True)))

    # ── 2. Profilo esteso (richiede una chiamata API in più) ─────
    sezioni.append(f"\n📇 {html.bold('Extended profile')}")
    try:
        chat_info = await message.bot.get_chat(user.id)
        # id/type/nomi/username duplicano la sezione precedente
        extra = {
            k: v
            for k, v in chat_info.model_dump(exclude_none=True).items()
            if k not in {"id", "type", "first_name", "last_name", "username"}
        }
        sezioni.append(_fmt_block(extra) or "No data.")
    except Exception as exc:
        logging.warning("userinfo: get_chat fallito: %s", exc)
        sezioni.append("Not available.")

    # ── 3. Foto profilo ──────────────────────────────────────────
    sezioni.append(f"\n🖼 {html.bold('Profile photos')}")
    try:
        photos = await message.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count and photos.photos:
            sezioni.append(f"{photos.total_count} photo(s) available")
            sezioni.append(_fmt_block({"latest_file_id": photos.photos[0][-1].file_id}))
        else:
            sezioni.append("No data.")
    except Exception as exc:
        logging.warning("userinfo: get_user_profile_photos fallito: %s", exc)
        sezioni.append("Not available.")

    # ── 4. Messaggio e chat ──────────────────────────────────────
    sezioni.append(f"\n💬 {html.bold('Message and chat')}")
    sezioni.append(_fmt_block({
        "message_id": message.message_id,
        "date": message.date.astimezone(TZ).isoformat(),
        "chat_id": message.chat.id,
        "chat_type": message.chat.type,
    }))

    # ── 5. Cosa il bot memorizza davvero ─────────────────────────
    sezioni.append(f"\n🗄 {html.bold('What the bot stores')}")
    stored = db_user_stored_data(user.id)
    if stored:
        sezioni.append("Your saved preferences:")
        sezioni.append(_fmt_block({k: v for k, v in stored.items() if v is not None}))
    else:
        sezioni.append("No preferences saved.")

    preferiti = db_preferiti_ids(user.id)
    sezioni.append(_fmt_block({
        "favourite_rooms": f"{len(preferiti)} / {MAX_PREFERITI}",
        "favourite_idaula": preferiti or "-",
    }))
    sezioni.append(f"\n{_STORED_NOTE}")

    await message.answer("\n".join(s for s in sezioni if s), disable_web_page_preview=True)
