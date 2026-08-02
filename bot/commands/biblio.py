"""
biblio.py – /biblio: occupazione biblioteche Polimi.
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from config import TZ
from db import get_conn, log_activity
from locales import t

router = Router()


# ── DB query ─────────────────────────────────────────────────────


def _fetch_all_sites_from_db() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (s.id)
                    s.name,
                    o.occupancy_percent,
                    o.is_open,
                    o.fetched_at
                FROM affluences_sites s
                JOIN affluences_occupancies o ON s.id = o.site_id
                ORDER BY s.id, o.fetched_at DESC
            """)
            return cur.fetchall()


# ── Formatting ───────────────────────────────────────────────────


def _occupancy_bar(pct: int) -> str:
    filled = round(pct / 10)
    return "█" * filled + "░" * (10 - filled)


def _short_name(full_name: str) -> str:
    return full_name.replace(" - Politecnico di Milano", "").strip()


def _format_all_sites(rows: list[dict], lang: str) -> str:
    lines = [f"📚 {html.bold(t(lang, 'biblio_header'))}"]

    if not rows:
        lines.append(t(lang, "biblio_no_data"))
        return "\n".join(lines)

    oldest_ts = min(r["fetched_at"] for r in rows)
    time_str = oldest_ts.astimezone(TZ).strftime("%H:%M")
    lines.append(f"<i>{t(lang, 'biblio_updated_at', time=time_str)}</i>")

    for row in rows:
        lines.append("")
        lines.append(f"🏛 {html.bold(_short_name(row['name']))}")

        is_open = row["is_open"]
        state_label = t(lang, "biblio_open") if is_open else t(lang, "biblio_closed")
        state_emoji = "🟢" if is_open else "🔴"
        lines.append(f"{state_emoji} {state_label}")

        pct = row["occupancy_percent"]
        if pct is not None:
            lines.append(t(lang, "biblio_occupancy", pct=pct))
            lines.append(f"<code>{_occupancy_bar(pct)}</code>")

    return "\n".join(lines)


# ── Handler ──────────────────────────────────────────────────────


@router.message(Command("biblio"))
async def cmd_biblio(message: Message, lang: str):
    log_activity("biblio")

    msg = await message.answer(t(lang, "biblio_loading"))

    try:
        rows = await asyncio.to_thread(_fetch_all_sites_from_db)
        text = _format_all_sites(rows, lang)
        await msg.edit_text(text, parse_mode="HTML")
    except Exception:
        logging.exception("biblio: errore fetch dati DB")
        await msg.edit_text(t(lang, "biblio_error"))
