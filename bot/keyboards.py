"""
keyboards.py – Costruttori di tastiere inline.

I callback_data sono generati dalle factory di callbacks.py: nessuna stringa
composta a mano.
"""

from datetime import date, datetime, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from callbacks import (
    AulaInfoCB,
    AulaWeekCB,
    FavToggleCB,
    HideCB,
    PageCB,
    SearchBackCB,
    SearchDurataCB,
    SearchGiornoCB,
    SearchOraCB,
)
from config import PAGE_SIZE, SEARCH_MAX_ORE, SEARCH_ORA_FINE, SEARCH_ORA_INIZIO, TZ
from formatters import fmt_giorno, format_aula_button
from locales import DEFAULT_LANG, t


def hide_keyboard(lang: str = DEFAULT_LANG) -> InlineKeyboardMarkup:
    """Pulsante per nascondere (eliminare) il messaggio."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "hide_message"), callback_data=HideCB().pack()),
    ]])


def aula_detail_keyboard(
    idaula: int, preferita: bool = False, lang: str = DEFAULT_LANG
) -> InlineKeyboardMarkup:
    """Sotto la scheda: toggle preferiti e occupazione dei prossimi giorni."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, "fav_remove" if preferita else "fav_add"),
            callback_data=FavToggleCB(idaula=idaula).pack(),
        )],
        [InlineKeyboardButton(
            text=t(lang, "aula_menu_week"),
            callback_data=AulaWeekCB(idaula=idaula).pack(),
        )],
    ])


def aule_keyboard(
    aule: list[dict],
    page: int,
    fascia: str,
    lang: str = DEFAULT_LANG,
    header_key: str = "aule_libere_header",
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Lista paginata di aule. `header_key` permette a /fav di riusare la stessa
    tastiera con un'altra intestazione: le chiavi che non usano {fascia} la
    ignorano, str.format() accetta argomenti in più.
    """
    totale  = len(aule)
    tot_pag = max(1, -(-totale // PAGE_SIZE))
    inizio  = page * PAGE_SIZE

    testo = t(lang, header_key, n=totale, fascia=fascia, page=page + 1, tot=tot_pag)

    kb: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(
            text=format_aula_button(a),
            callback_data=AulaInfoCB(idaula=a["idaula"]).pack(),
        )]
        for a in aule[inizio: inizio + PAGE_SIZE]
    ]

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=t(lang, "prev_page"), callback_data=PageCB(page=page - 1).pack()
        ))
    if inizio + PAGE_SIZE < totale:
        nav.append(InlineKeyboardButton(
            text=t(lang, "next_page"), callback_data=PageCB(page=page + 1).pack()
        ))
    if nav:
        kb.append(nav)

    return testo, InlineKeyboardMarkup(inline_keyboard=kb)


# ── Tastiere /search ──────────────────────────────────────────────

def search_giorni_kb(lang: str = DEFAULT_LANG) -> InlineKeyboardMarkup:
    """I prossimi 7 giorni feriali, oggi incluso se feriale."""
    d = datetime.now(TZ).date()
    giorni: list[date] = [d] if d.weekday() < 5 else []
    while len(giorni) < 7:
        d += timedelta(days=1)
        if d.weekday() < 5:
            giorni.append(d)

    righe = [
        [
            InlineKeyboardButton(
                text=fmt_giorno(g, lang),
                callback_data=SearchGiornoCB(giorno=g.isoformat()).pack(),
            )
            for g in giorni[i:i + 2]
        ]
        for i in range(0, len(giorni), 2)
    ]
    return InlineKeyboardMarkup(inline_keyboard=righe)


def search_ore_kb(giorno: date, lang: str = DEFAULT_LANG) -> InlineKeyboardMarkup:
    pulsanti = [
        InlineKeyboardButton(
            text=f"{h:02d}:00",
            callback_data=SearchOraCB(giorno=giorno.isoformat(), ora=h).pack(),
        )
        for h in range(SEARCH_ORA_INIZIO, SEARCH_ORA_FINE)
    ]
    righe = [pulsanti[i:i + 4] for i in range(0, len(pulsanti), 4)]
    righe.append([InlineKeyboardButton(
        text=t(lang, "search_back_day"), callback_data=SearchBackCB().pack()
    )])
    return InlineKeyboardMarkup(inline_keyboard=righe)


def search_durata_kb(giorno: date, ora: int, lang: str = DEFAULT_LANG) -> InlineKeyboardMarkup:
    max_ore = min(SEARCH_MAX_ORE, SEARCH_ORA_FINE - ora)
    pulsanti = [
        InlineKeyboardButton(
            text=f"{d}h",
            callback_data=SearchDurataCB(
                giorno=giorno.isoformat(), ora=ora, durata=d
            ).pack(),
        )
        for d in range(1, max_ore + 1)
    ]
    back = InlineKeyboardButton(
        text=t(lang, "search_back_hour"),
        callback_data=SearchGiornoCB(giorno=giorno.isoformat()).pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[pulsanti, [back]])


def search_nuova_kb(lang: str = DEFAULT_LANG) -> InlineKeyboardMarkup:
    """Unico pulsante 'Nuova ricerca', mostrato quando non ci sono risultati."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "search_new"), callback_data=SearchBackCB().pack()),
    ]])
