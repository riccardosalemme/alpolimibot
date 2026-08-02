"""
aule.py – Query su aule, sedi e occupazione.

Note sulle query:
 * la tolleranza sulla fine dello slot viene da config, così SQL e Python non
   possono divergere;
 * `preferita` si calcola con un EXISTS dentro la query stessa: niente seconda
   interrogazione né riordino in Python.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from config import TOLLERANZA_FINE_SLOT_MIN, TZ
from db.pool import get_conn

# Blocco riusato da tutte le query che restituiscono una scheda aula.
_AULA_FIELDS = """
    a.idaula,
    a.sigla,
    a.capienza,
    e.nome                AS edificio,
    ca.nome               AS campus,
    s.nome                AS sede,
    a.has_power_sockets   AS has_power_sockets,
    a.has_network_sockets AS has_network_sockets,
    EXISTS (
        SELECT 1 FROM user_favourite uf
        WHERE uf.user_id = %(user_id)s AND uf.idaula = a.idaula
    ) AS preferita
"""

_AULA_JOINS = """
    FROM aula a
    JOIN edificio e  ON e.csie  = a.csie
    JOIN campus   ca ON ca.csic = e.csic
    JOIN sede     s  ON s.csis  = a.csis
"""


# ── Sedi ──────────────────────────────────────────────────────────

def db_sedi_visibili() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT csis, nome FROM sede WHERE show = TRUE ORDER BY nome")
            return [dict(r) for r in cur.fetchall()]


# ── Ricerca aule ──────────────────────────────────────────────────

def db_aule_libere(sede_csis: str, da: datetime, a: datetime, user_id: int) -> list[dict]:
    """
    Aule visibili della sede senza occupazione sovrapposta a [da, a].
    Le preferite dell'utente vengono marcate e ordinate per prime.
    """
    sql = f"""
        SELECT {_AULA_FIELDS}
        {_AULA_JOINS}
        WHERE a.csis = %(sede_csis)s
          AND a.visible = TRUE
          AND NOT EXISTS (
              SELECT 1
              FROM occupazione_giorno og
              JOIN occupazione_slot   os ON os.id_giorno = og.id
              WHERE og.idaula = a.idaula
                AND og.data   = %(giorno)s
                AND os.inizio < %(a)s
                AND os.fine - (%(tolleranza)s * interval '1 minute') > %(da)s
          )
        ORDER BY preferita DESC, a.sort DESC, a.has_power_sockets DESC, a.sigla
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "sede_csis":  sede_csis,
                "giorno":     da.date(),
                "da":         da.strftime("%H:%M"),
                "a":          a.strftime("%H:%M"),
                "tolleranza": TOLLERANZA_FINE_SLOT_MIN,
                "user_id":    user_id,
            })
            return [dict(r) for r in cur.fetchall()]


def _normalize_sigla(sigla: str) -> str:
    return sigla.replace(".", "").replace(" ", "").upper()


def db_cerca_aula(sigla: str, user_id: int) -> Optional[dict]:
    """Ricerca per sigla, tollerante a punti e spazi. Preferisce il match esatto."""
    sql = f"""
        SELECT {_AULA_FIELDS}
        {_AULA_JOINS}
        WHERE a.visible = TRUE
          AND (
              UPPER(a.sigla) = UPPER(%(sigla)s)
              OR REPLACE(REPLACE(UPPER(a.sigla), '.', ''), ' ', '') = %(sigla_norm)s
          )
        ORDER BY
            CASE WHEN UPPER(a.sigla) = UPPER(%(sigla)s) THEN 0 ELSE 1 END,
            a.sort DESC
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "sigla":      sigla,
                "sigla_norm": _normalize_sigla(sigla),
                "user_id":    user_id,
            })
            row = cur.fetchone()
    return dict(row) if row else None


def db_cerca_aula_by_id(idaula: int, user_id: int) -> Optional[dict]:
    sql = f"""
        SELECT {_AULA_FIELDS}
        {_AULA_JOINS}
        WHERE a.idaula = %(idaula)s
          AND a.visible = TRUE
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"idaula": idaula, "user_id": user_id})
            row = cur.fetchone()
    return dict(row) if row else None


# ── Occupazione ───────────────────────────────────────────────────

def db_occupazione_giorno(idaula: int, giorno: date) -> list[dict]:
    sql = """
        SELECT os.inizio::TEXT, os.fine::TEXT, os.corso
        FROM occupazione_slot   os
        JOIN occupazione_giorno og ON og.id = os.id_giorno
        WHERE og.idaula = %(idaula)s
          AND og.data   = %(giorno)s
        ORDER BY os.inizio
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"idaula": idaula, "giorno": giorno})
            return [dict(r) for r in cur.fetchall()]


def db_occupazione_settimana(idaula: int) -> dict[str, list[dict]]:
    """
    Occupazione dell'aula per i prossimi 7 giorni feriali (incluso oggi se
    feriale). Chiavi: date ISO; valori: lista di slot con il nome del corso.
    """
    oggi = datetime.now(TZ).date()
    giorni: list[date] = []
    d = oggi
    while len(giorni) < 7:
        if d.weekday() < 5:
            giorni.append(d)
        d += timedelta(days=1)

    sql = """
        SELECT og.data::TEXT, os.inizio::TEXT, os.fine::TEXT, os.corso
        FROM occupazione_slot   os
        JOIN occupazione_giorno og ON og.id = os.id_giorno
        WHERE og.idaula = %(idaula)s
          AND og.data  >= %(oggi)s
          AND og.data  <= %(fine)s
        ORDER BY og.data, os.inizio
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"idaula": idaula, "oggi": oggi, "fine": giorni[-1]})
            rows = [dict(r) for r in cur.fetchall()]

    result: dict[str, list[dict]] = {g.isoformat(): [] for g in giorni}
    for row in rows:
        if row["data"] in result:
            result[row["data"]].append({
                "inizio": row["inizio"],
                "fine":   row["fine"],
                "corso":  row.get("corso"),
            })
    return result
