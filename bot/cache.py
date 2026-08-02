"""
cache.py – Cache in-memory con TTL per le liste di aule.

Sostituisce la cache Redis: il bot gira come processo singolo, quindi un
dizionario di modulo basta e non costa I/O.

Chiave: message_id del messaggio che contiene la lista
Valore: dict con aule (solo i campi usati dalla tastiera), fascia, lang, giorno
TTL:    1 ora – le ricerche scadono naturalmente
"""

import time

from config import AULE_CACHE_MAXSIZE, AULE_CACHE_TTL


class TTLCache:
    def __init__(self, ttl: int = AULE_CACHE_TTL, maxsize: int = AULE_CACHE_MAXSIZE) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._data: dict[int, tuple[float, dict]] = {}

    def _prune(self) -> None:
        now = time.monotonic()
        for key in [k for k, (exp, _) in self._data.items() if exp <= now]:
            del self._data[key]

        # Ancora sopra il tetto: elimina le voci con scadenza più vicina.
        if len(self._data) >= self._maxsize:
            per_scadenza = sorted(self._data.items(), key=lambda kv: kv[1][0])
            for key, _ in per_scadenza[: len(self._data) - self._maxsize + 1]:
                del self._data[key]

    def __setitem__(self, key: int, value: dict) -> None:
        self._prune()
        self._data[key] = (time.monotonic() + self._ttl, value)

    def get(self, key: int) -> dict | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        scadenza, value = entry
        if scadenza <= time.monotonic():
            del self._data[key]
            return None
        return value


# Istanza unica condivisa da /now e /search: il callback di paginazione vive in
# now.py e deve poter leggere anche le liste prodotte da /search.
aule_cache = TTLCache()


def slim_aula(aula: dict) -> dict:
    """Solo i campi usati da aule_keyboard; la scheda dettaglio ricarica dal DB."""
    return {
        "idaula": aula["idaula"],
        "sigla": aula["sigla"],
        "has_power_sockets": aula.get("has_power_sockets"),
        "preferita": aula.get("preferita"),
        # None = stato non pertinente; solo /fav lo valorizza. Resta congelato
        # per tutta la vita della voce in cache: è una fotografia, come la lista.
        "occupata": aula.get("occupata"),
    }
