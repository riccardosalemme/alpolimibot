"""
config.py – Tutte le costanti regolabili del bot, in un posto solo.

Qui stanno solo valori: nessun import dal resto del progetto, così qualunque
modulo può importarlo senza rischio di cicli.
"""

from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")

# ── Interfaccia ───────────────────────────────────────────────────
PAGE_SIZE = 8                  # aule per pagina nelle liste
MAX_PREFERITI = 50             # aule preferite per utente

# Comandi mostrati nel menu "/" di Telegram, nell'ordine.
# La descrizione di ognuno sta in locales.json alla chiave "cmd_<nome>".
# /userinfo è volutamente escluso: è diagnostico, non di uso quotidiano.
COMANDI_MENU = (
    "start",
    "settings",
    "now",
    "search",
    "fav",
    "biblio",
    "report",
    "help",
    "about",
)

# ── Ricerca (/search) ─────────────────────────────────────────────
SEARCH_ORA_INIZIO = 8
SEARCH_ORA_FINE   = 20
SEARCH_MAX_ORE    = 4

# ── Occupazione ───────────────────────────────────────────────────
# Un'aula con slot 13:15–16:15 è considerata libera già dalle 16:00.
# Usato sia dalle query SQL sia dal calcolo in Python: tenerlo in un solo
# posto evita che le due letture si contraddicano.
TOLLERANZA_FINE_SLOT_MIN = 15

# ── Cache in-process ──────────────────────────────────────────────
AULE_CACHE_TTL     = 3600      # le liste di aule scadono dopo un'ora
AULE_CACHE_MAXSIZE = 500       # tetto di sicurezza sulla memoria
PREF_CACHE_TTL     = 600       # rete di sicurezza se il DB cambia a mano

# ── Activity log ──────────────────────────────────────────────────
SIGLA_MAX = 50                 # la sigla arriva da testo libero dell'utente

# ── /userinfo ─────────────────────────────────────────────────────
USERINFO_MAX_VALUE_LEN = 300

# ── Risorse esterne ───────────────────────────────────────────────
FOTO_DIR = Path("data/foto/aule")
POLIMI_AULA_URL = "https://onlineservices.polimi.it/spazi/spazi/controller/Aula.do?idaula={idaula}"
