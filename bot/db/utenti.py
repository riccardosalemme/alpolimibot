"""
utenti.py – Preferenze, aule preferite e segnalazioni.

Unico punto del progetto in cui un user_id finisce su disco, e solo per dati
che l'utente ha scelto esplicitamente: sede, lingua, preferiti. Le statistiche
d'uso e le segnalazioni restano anonime (vedi activity.py e db_save_report).
"""

from datetime import datetime
from time import monotonic
from typing import Optional

from config import MAX_PREFERITI, PREF_CACHE_TTL, TOLLERANZA_FINE_SLOT_MIN
from db.pool import get_conn

# ── Preferenze ────────────────────────────────────────────────────

# Cache in-process: il bot è l'unico scrittore e gira come processo singolo,
# quindi resta sempre coerente. Il TTL serve solo se il DB cambia a mano.
_pref_cache: dict[int, tuple[float, Optional[dict]]] = {}


def db_get_preference(user_id: int) -> Optional[dict]:
    entry = _pref_cache.get(user_id)
    if entry is not None:
        scadenza, cached = entry
        if scadenza > monotonic():
            return cached
        del _pref_cache[user_id]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sede_name, sede_csis, language FROM user_preference WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    result = dict(row) if row else None
    # Anche l'assenza di preferenze va in cache: altrimenti ogni messaggio di
    # un utente non configurato costerebbe una query.
    _pref_cache[user_id] = (monotonic() + PREF_CACHE_TTL, result)
    return result


def db_save_preference(
    user_id: int,
    sede_name: Optional[str],
    sede_csis: Optional[str],
    language: str = "it",
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_preference (user_id, sede_name, sede_csis, language, aggiornato_il)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE
                    SET sede_name     = EXCLUDED.sede_name,
                        sede_csis     = EXCLUDED.sede_csis,
                        language      = EXCLUDED.language,
                        aggiornato_il = NOW()
                """,
                (user_id, sede_name, sede_csis, language),
            )
    _pref_cache.pop(user_id, None)


def db_user_stored_data(user_id: int) -> Optional[dict]:
    """Riga completa di user_preference: usata da /userinfo."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sede_name, sede_csis, language, aggiornato_il "
                "FROM user_preference WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    return dict(row) if row else None


# ── Aule preferite ────────────────────────────────────────────────

def db_preferiti_ids(user_id: int) -> list[int]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT idaula FROM user_favourite WHERE user_id = %s", (user_id,))
            return [r["idaula"] for r in cur.fetchall()]


def db_toggle_preferito(user_id: int, idaula: int) -> tuple[bool, bool]:
    """
    Aggiunge o rimuove l'aula dai preferiti. Ritorna (preferita_adesso, limite_raggiunto).

    DELETE, conteggio e INSERT stanno nella stessa transazione, quindi il
    limite non è aggirabile con due click ravvicinati.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_favourite WHERE user_id = %s AND idaula = %s",
                (user_id, idaula),
            )
            if cur.rowcount:
                return False, False

            cur.execute(
                "SELECT COUNT(*) AS n FROM user_favourite WHERE user_id = %s",
                (user_id,),
            )
            if cur.fetchone()["n"] >= MAX_PREFERITI:
                return False, True

            cur.execute(
                "INSERT INTO user_favourite (user_id, idaula) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (user_id, idaula),
            )
            return True, False


def db_aule_preferite(user_id: int, adesso: datetime) -> list[dict]:
    """
    Aule preferite dell'utente con lo stato di occupazione a `adesso`.

    Una sola query: l'EXISTS correlato evita di interrogare l'occupazione aula
    per aula. Stessa tolleranza usata da db_aule_libere, altrimenti /fav e /now
    si contraddirebbero sulla stessa aula.
    """
    sql = """
        SELECT
            a.idaula,
            a.sigla,
            a.has_power_sockets,
            EXISTS (
                SELECT 1
                FROM occupazione_giorno og
                JOIN occupazione_slot   os ON os.id_giorno = og.id
                WHERE og.idaula = a.idaula
                  AND og.data   = %(giorno)s
                  AND os.inizio <= %(ora)s
                  AND os.fine - (%(tolleranza)s * interval '1 minute') > %(ora)s
            ) AS occupata
        FROM user_favourite uf
        JOIN aula a ON a.idaula = uf.idaula
        WHERE uf.user_id = %(user_id)s
          AND a.visible  = TRUE
        ORDER BY a.sigla
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "user_id":    user_id,
                "giorno":     adesso.date(),
                "ora":        adesso.strftime("%H:%M"),
                "tolleranza": TOLLERANZA_FINE_SLOT_MIN,
            })
            rows = cur.fetchall()
    return [dict(r) for r in rows]


# ── Segnalazioni ──────────────────────────────────────────────────

def db_save_report(messaggio: str) -> None:
    """Salva una segnalazione anonima: solo testo e timestamp."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO report (messaggio) VALUES (%s)", (messaggio,))
