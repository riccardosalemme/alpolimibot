"""
callbacks.py – Definizioni tipizzate dei callback_data.

Sostituisce il parsing a mano (`callback.data.split("_")[1]`), che rompeva in
silenzio con un IndexError appena un formato cambiava. aiogram impacchetta e
spacchetta da sé, e il filtro `.filter()` garantisce che l'handler riceva solo
callback della forma giusta.

Vincoli da tenere a mente:
 * il separatore è `:`, quindi nessun valore può contenerlo (niente orari come
   "13:00 – 14:00": la fascia si legge dalla cache, dove già sta);
 * i tipi impacchettabili sono int/str/float/bool/Decimal/Enum/UUID: le date
   viaggiano come stringa ISO e si riconvertono con date.fromisoformat();
 * il totale non può superare i 64 byte.
"""

from aiogram.filters.callback_data import CallbackData


class AulaInfoCB(CallbackData, prefix="ai"):
    """Apre la scheda di un'aula dalla lista risultati."""
    idaula: int


class AulaWeekCB(CallbackData, prefix="aw"):
    """Occupazione dei prossimi giorni per un'aula."""
    idaula: int


class FavToggleCB(CallbackData, prefix="ft"):
    """Aggiunge o rimuove l'aula dai preferiti."""
    idaula: int


class PageCB(CallbackData, prefix="pg"):
    """Cambio pagina in una lista di aule. Il resto dello stato sta in cache."""
    page: int


class HideCB(CallbackData, prefix="hd"):
    """Elimina il messaggio."""


class SettingsCB(CallbackData, prefix="st"):
    """Scelta della voce da modificare in /settings."""
    campo: str          # "lang" | "sede"


class SearchBackCB(CallbackData, prefix="sb"):
    """Torna alla scelta del giorno in /search."""


class SearchGiornoCB(CallbackData, prefix="sg"):
    giorno: str         # ISO (YYYY-MM-DD)


class SearchOraCB(CallbackData, prefix="so"):
    giorno: str         # ISO
    ora: int


class SearchDurataCB(CallbackData, prefix="sd"):
    giorno: str         # ISO
    ora: int
    durata: int
