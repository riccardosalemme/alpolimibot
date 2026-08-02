"""
db – Accesso al database, diviso per area.

    pool.py      connection pool e transazioni
    activity.py  log d'uso anonimo
    utenti.py    preferenze, aule preferite, segnalazioni
    aule.py      aule, sedi, occupazione

I moduli si importano anche direttamente (`from db.aule import ...`); questo
__init__ riespone l'API pubblica per non spezzare gli import esistenti.
"""

from db.activity import log_activity
from db.aule import (
    db_aule_libere,
    db_cerca_aula,
    db_cerca_aula_by_id,
    db_occupazione_giorno,
    db_occupazione_settimana,
    db_sedi_visibili,
)
from db.pool import close_pool, get_conn, init_pool
from db.utenti import (
    db_aule_preferite,
    db_get_preference,
    db_preferiti_ids,
    db_save_preference,
    db_save_report,
    db_toggle_preferito,
    db_user_stored_data,
)

__all__ = [
    "close_pool",
    "db_aule_libere",
    "db_aule_preferite",
    "db_cerca_aula",
    "db_cerca_aula_by_id",
    "db_get_preference",
    "db_occupazione_giorno",
    "db_occupazione_settimana",
    "db_preferiti_ids",
    "db_save_preference",
    "db_save_report",
    "db_sedi_visibili",
    "db_toggle_preferito",
    "db_user_stored_data",
    "get_conn",
    "init_pool",
    "log_activity",
]
