"""
Scarica gli orari di occupazione per ogni aula memorizzata nel database
e li salva nelle tabelle occupazione_giorno e occupazione_slot.

Per alcune aule non è possibile scaricare l'occupazione. In questi casi
vedrete comparire un messaggio di errore 400 nei log.

Per default scarica l'occupazione di OGGI. Con --giorni N scarica
gli N giorni successivi a partire da oggi (utile per backfill o previsione).
Con --data YYYY-MM-DD scarica un giorno specifico.

Utilizzo:
    uv run jobs/spazi/4_occupazione.py                     # solo oggi
    uv run jobs/spazi/4_occupazione.py --giorni 7          # oggi + 6 giorni
    uv run jobs/spazi/4_occupazione.py --data 2026-03-10   # giorno specifico
    uv run jobs/spazi/4_occupazione.py --workers 8         # parallelismo HTTP
"""

import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from dotenv import load_dotenv
import psycopg2
import requests
from psycopg2.extras import execute_values

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.getenv("PGHOST"),
    "port":     int(os.getenv("PGPORT", "5432")),
    "dbname":   os.getenv("PGDATABASE"),
    "user":     os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}

BASE_URL = "https://onlineservices.polimi.it/maps_rest/rest"

HEADERS = {
    "host": "onlineservices.polimi.it",
    "poliauthprofile": "0",
    "poliauthd_profile": "JAF_D_PROFILE_VUOTO",
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 15; M2007J20CG Build/BP1A.250505.005; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.76 "
        "Mobile Safari/537.36"
    ),
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "x-requested-with": "it.polimi.polimimobile",
}

REQUEST_DELAY = 0.05 # Ritardo tra le richieste HTTP (secondi)
MAX_RETRIES = 1 # Numero di tentativi in caso di errore


# ==================================================================
# HTTP helper
# ==================================================================

def fetch_occupazione(idaula: int, data: date, retry: int = 0) -> list[dict] | None:
    """
    Chiama GET /ricerca/aula/occupazione/{idaula}/{YYYYMMDD}
    Restituisce la lista di slot [{inizio, fine}] o None in caso di errore.
    """
    data_str = data.strftime("%Y%m%d")
    url = f"{BASE_URL}/ricerca/aula/occupazione/{idaula}/{data_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429 and retry < MAX_RETRIES:
            wait = 2 ** retry
            log.warning("Rate limit su aula %d, attendo %ds…", idaula, wait)
            time.sleep(wait)
            return fetch_occupazione(idaula, data, retry + 1)
        log.error("HTTP %d per aula %d data %s", resp.status_code, idaula, data_str)
        return None
    except Exception as exc:
        if retry < MAX_RETRIES:
            time.sleep(1)
            return fetch_occupazione(idaula, data, retry + 1)
        log.error("Errore aula %d data %s: %s", idaula, data_str, exc)
        return None


# ==================================================================
# DB helpers
# ==================================================================

def load_idaule(conn) -> list[int]:
    """Recupera tutti gli idaula presenti nel database."""
    with conn.cursor() as cur:
        cur.execute("SELECT idaula FROM aula ORDER BY idaula")
        return [row[0] for row in cur.fetchall()]


def upsert_occupazione(conn, idaula: int, data: date, slots: list[dict]) -> None:
    """
    Inserisce o aggiorna l'occupazione di un'aula per un giorno.
    Strategia:
      1. Upsert su occupazione_giorno → ottieni l'id del giorno
      2. Cancella gli slot esistenti per quell'id_giorno
      3. Reinserisce gli slot aggiornati
    """
    with conn.cursor() as cur:
        # 1. Upsert del giorno (aggiorna scaricato_il se già esiste)
        cur.execute(
            """
            INSERT INTO occupazione_giorno (idaula, data, scaricato_il)
            VALUES (%s, %s, NOW())
            ON CONFLICT (idaula, data) DO UPDATE
                SET scaricato_il = NOW()
            RETURNING id
            """,
            (idaula, data),
        )
        id_giorno = cur.fetchone()[0]

        # 2. Pulisce gli slot precedenti
        cur.execute("DELETE FROM occupazione_slot WHERE id_giorno = %s", (id_giorno,))

        # 3. Inserisce i nuovi slot
        if slots:
            rows = [
                (id_giorno, s["inizio"], s["fine"])
                for s in slots
                if "inizio" in s and "fine" in s
            ]
            if rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO occupazione_slot (id_giorno, inizio, fine)
                    VALUES %s
                    ON CONFLICT (id_giorno, inizio) DO NOTHING
                    """,
                    rows,
                )

    conn.commit()


# ==================================================================
# Worker
# ==================================================================

def process_aula(idaula: int, giorni: list[date], db_config: dict) -> dict:
    """
    Scarica e salva l'occupazione per una singola aula su tutti i giorni richiesti.
    Usa una connessione DB dedicata (necessario per il multithreading).
    Restituisce un dizionario con i contatori per il log finale.
    """
    conn = psycopg2.connect(**db_config)
    ok = 0
    errori = 0

    try:
        for giorno in giorni:
            slots = fetch_occupazione(idaula, giorno)
            time.sleep(REQUEST_DELAY)

            if slots is None:
                errori += 1
                continue

            upsert_occupazione(conn, idaula, giorno, slots)
            ok += 1

    finally:
        conn.close()

    return {"idaula": idaula, "ok": ok, "errori": errori}


# ==================================================================
# Main
# ==================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scarica gli orari di occupazione delle aule Polimi."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--giorni", "-g",
        type=int,
        default=1,
        metavar="N",
        help="Numero di giorni da scaricare a partire da oggi (default: 1 = solo oggi)",
    )
    group.add_argument(
        "--data", "-d",
        type=str,
        metavar="YYYY-MM-DD",
        help="Scarica un singolo giorno specifico",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        metavar="N",
        help="Numero di thread paralleli per le richieste HTTP (default: 4)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Calcola la lista di giorni da scaricare
    if args.data:
        try:
            giorni = [date.fromisoformat(args.data)]
        except ValueError:
            log.error("Formato data non valido: usa YYYY-MM-DD")
            raise
    else:
        oggi = date.today()
        giorni = [oggi + timedelta(days=i) for i in range(args.giorni)]

    log.info(
        "Giorni da scaricare: %d  (%s → %s)",
        len(giorni), giorni[0], giorni[-1],
    )

    # Recupera la lista di aule dal DB
    conn = psycopg2.connect(**DB_CONFIG)
    idaule = load_idaule(conn)
    conn.close()
    log.info("Aule trovate nel database: %d", len(idaule))

    totale = len(idaule) * len(giorni)
    log.info(
        "Richieste HTTP totali: %d aule × %d giorni = %d  (workers: %d)",
        len(idaule), len(giorni), totale, args.workers,
    )

    ok_tot = errori_tot = 0
    completate = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_aula, idaula, giorni, DB_CONFIG): idaula
            for idaula in idaule
        }
        for future in as_completed(futures):
            result = future.result()
            ok_tot      += result["ok"]
            errori_tot  += result["errori"]
            completate  += 1
            if completate % 10 == 0 or completate == len(idaule):
                log.info(
                    "Progresso: %d/%d aule  |  slot salvati: %d  |  errori: %d",
                    completate, len(idaule), ok_tot, errori_tot,
                )

    log.info(
        "Download completato — giorni OK: %d  |  errori: %d",
        ok_tot, errori_tot,
    )


if __name__ == "__main__":
    main()