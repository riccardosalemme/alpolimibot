"""
formatters.py – Costruzione dei testi mostrati all'utente.

Solo formattazione: niente query, niente chiamate a Telegram.
"""

import re
from datetime import date, datetime, timedelta

from aiogram import html

from config import POLIMI_AULA_URL, TOLLERANZA_FINE_SLOT_MIN, TZ
from locales import DEFAULT_LANG, get_weekdays, t


# ── Date ──────────────────────────────────────────────────────────

def fmt_giorno(d: date, lang: str = DEFAULT_LANG) -> str:
    if d == datetime.now(TZ).date():
        return f"{t(lang, 'today')} {d.strftime('%d/%m')}"
    return f"{get_weekdays(lang)[d.weekday()]} {d.strftime('%d/%m')}"


# ── Stato occupazione ─────────────────────────────────────────────

def is_now_occupied(slots: list[dict]) -> bool:
    """
    True se l'aula è occupata ora. Applica la stessa tolleranza sulla fine
    dello slot usata dalle query SQL (config.TOLLERANZA_FINE_SLOT_MIN).
    """
    now_time = datetime.now(TZ).time().replace(second=0, microsecond=0)
    tolleranza = timedelta(minutes=TOLLERANZA_FINE_SLOT_MIN)
    for s in slots:
        inizio = datetime.strptime(s["inizio"][:5], "%H:%M").time()
        fine = (datetime.strptime(s["fine"][:5], "%H:%M") - tolleranza).time()
        if inizio <= now_time < fine:
            return True
    return False


# ── Schede aula ───────────────────────────────────────────────────

def format_aula_card(aula: dict, slots: list[dict], giorno: date, lang: str = DEFAULT_LANG) -> str:
    """Scheda aula completa: sigla, campus, capienza, stato, occupazione, link."""
    url = POLIMI_AULA_URL.format(idaula=aula["idaula"])

    edificio = aula.get("edificio", "")
    location = aula.get("campus", "N/D")
    if edificio:
        location += f" – {edificio}"

    cap = aula.get("capienza")
    cap_str = t(lang, "aula_capacity", cap=cap) if cap else t(lang, "aula_capacity_nd")

    linee = [
        f"📍 {html.bold('Aula ' + aula['sigla'])}",
        f"🏛 {location}",
        cap_str,
    ]

    if aula.get("has_power_sockets"):
        linee.append(t(lang, "aula_power"))
    if aula.get("has_network_sockets"):
        linee.append(t(lang, "aula_network"))

    if giorno == datetime.now(TZ).date():
        stato = "aula_now_occupied" if is_now_occupied(slots) else "aula_now_free"
        linee.append(t(lang, stato))

    linee.extend(["", f"📅 {html.bold(fmt_giorno(giorno, lang))}:"])

    if not slots:
        linee.append(f"  {t(lang, 'aula_no_slots')}")
    else:
        for s in slots:
            corso = s.get("corso") or ""
            corso_str = f"\n{corso}" if corso else ""
            linee.append(
                f"{html.bold(s['inizio'][:5])} – {html.bold(s['fine'][:5])} "
                f"\n<blockquote>{corso_str}</blockquote>"
            )

    linee.extend(["", f"🔗 <a href=\"{url}\">{t(lang, 'aula_link')}</a>"])
    return "\n".join(linee)


# Codice corso in coda al nome, es. "Analisi matematica 1  051234"
_CODICE_CORSO = re.compile(r"\s+\d{6}\b")


def format_aula_settimana(aula: dict, week_slots: dict, lang: str = DEFAULT_LANG) -> str:
    """Occupazione dei prossimi 7 giorni feriali con nome corso."""
    linee = [f"📅 {html.bold(t(lang, 'aula_week_header', sigla=aula['sigla']))}"]
    ultimo_giorno = list(week_slots)[-1] if week_slots else None

    for data_str, slots in week_slots.items():
        linee.append("")
        linee.append(f"📅 {html.bold(fmt_giorno(date.fromisoformat(data_str), lang))}: \n")

        if not slots:
            linee.append(f"  {t(lang, 'aula_no_slots')}")
        else:
            for s in slots:
                corso = s.get("corso") or ""
                nome = _CODICE_CORSO.split(corso)[0]
                linee.append(
                    f"{html.bold(s['inizio'][:5])} - {html.bold(s['fine'][:5])} "
                    f"\n<blockquote>{nome}</blockquote>"
                )

        if data_str != ultimo_giorno:
            linee.append("_" * 20)

    return "\n".join(linee)


def format_aula_button(aula: dict) -> str:
    """
    Prefissi del bottone. `occupata` vale None quando lo stato non è pertinente
    (in /now e /search le aule elencate sono libere per costruzione): solo /fav
    lo valorizza, così i simboli non si accavallano mai.
    """
    stella = "⭐ " if aula.get("preferita") else ""
    occupata = aula.get("occupata")
    stato = "" if occupata is None else ("🔴 " if occupata else "🟢 ")
    presa = "🔌 " if aula.get("has_power_sockets") else ""
    return f"{stella}{stato}{presa}{aula['sigla']}"
