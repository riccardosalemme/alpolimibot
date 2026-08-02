"""
activity.py – Log d'uso anonimo.

Nessun identificativo dell'utente entra in questa tabella: solo l'azione, i
parametri della richiesta e il timestamp. Ogni parametro ha la sua colonna,
così le statistiche si scrivono in SQL puro.
"""

import logging
from datetime import date, time
from typing import Optional

from config import SIGLA_MAX
from db.pool import get_conn


def log_activity(
    action: str,
    *,
    sede_csis: Optional[str] = None,
    idaula: Optional[int] = None,
    sigla: Optional[str] = None,
    giorno: Optional[date] = None,
    ora_inizio: Optional[time] = None,
    ora_fine: Optional[time] = None,
    language: Optional[str] = None,
) -> None:
    """Best-effort: un errore qui non deve mai far fallire il comando."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO activity_log
                        (action, sede_csis, idaula, sigla, giorno, ora_inizio, ora_fine, language)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (action, sede_csis, idaula, sigla[:SIGLA_MAX] if sigla else None,
                     giorno, ora_inizio, ora_fine, language),
                )
    except Exception as exc:
        logging.warning("log_activity fallito: %s", exc)
