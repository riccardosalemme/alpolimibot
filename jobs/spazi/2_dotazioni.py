"""
Scarica le dotazioni per ogni aula presente nel database e aggiorna:
  - tipo_dotazione   (lookup dei tipi)
  - aula_dotazione   (relazione M:N aula ↔ tipo)
  - aula.has_power_sockets   (TRUE se l'aula ha prese elettriche)
  - aula.has_network_sockets (TRUE se l'aula ha prese di rete ethernet)

Utilizzo:
    uv run jobs/spazi/2_dotazioni.py
    uv run jobs/spazi/2_dotazioni.py --workers 4
"""

import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 15; M2007J20CG Build/BP1A.250505.005; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.76 "
        "Mobile Safari/537.36"
    ),
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
}

BASE_URL = "https://onlineservices.polimi.it/maps_rest/rest"

DB_CONFIG = {
    "host":     os.getenv("PGHOST"),
    "port":     int(os.getenv("PGPORT", "5432")),
    "dbname":   os.getenv("PGDATABASE"),
    "user":     os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}

REQUEST_DELAY = 0.1  # secondi tra una richiesta e l'altra
KEYWORDS_POWER  = ["presa elettrica"] # id_dotazione = 142
KEYWORDS_NETWORK = ["presa di rete"] # id_dotazione = 143


# ==================================================================
# Helpers
# ==================================================================

def _has_keyword(label: str, keywords: list[str]) -> bool:
    label_lower = label.lower()
    return any(kw in label_lower for kw in keywords)


def fetch_dotazioni(idaula: int) -> list[dict]:
    url = f"{BASE_URL}/ricerca/aula/dotazioni/{idaula}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            log.warning("HTTP %d per dotazioni aula %d", resp.status_code, idaula)
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as exc:
        log.warning("Errore richiesta dotazioni aula %d: %s", idaula, exc)
        return []


def load_idaule(conn) -> list[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT idaula FROM aula ORDER BY idaula")
        return [row[0] for row in cur.fetchall()]


# ==================================================================
# Import helpers
# ==================================================================

def upsert_tipo_dotazioni(cur, tipi: dict[int, dict]) -> None:
    if not tipi:
        return
    rows = [(t["id"], t["it"], t["en"]) for t in tipi.values()]
    execute_values(
        cur,
        """
        INSERT INTO tipo_dotazione (id, it, en)
        VALUES %s
        ON CONFLICT (id) DO UPDATE
            SET it = EXCLUDED.it,
                en = EXCLUDED.en
        """,
        rows,
    )


def replace_aula_dotazioni(cur, idaula: int, dotazioni: list[dict]) -> None:
    """Sostituisce le dotazioni di un'aula (delete + insert)."""
    cur.execute("DELETE FROM aula_dotazione WHERE idaula = %s", (idaula,))
    rows = []
    for dot in dotazioni:
        if not isinstance(dot, dict):
            continue
        try:
            rows.append((idaula, int(dot["id"])))
        except (KeyError, TypeError, ValueError):
            continue
    if rows:
        execute_values(
            cur,
            """
            INSERT INTO aula_dotazione (idaula, id_tipo_dotazione)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            rows,
        )


def update_aula_socket_flags(cur, idaula: int, dotazioni: list[dict]) -> None:
    """Aggiorna has_power_sockets e has_network_sockets sull'aula."""
    has_power   = False
    has_network = False
    for dot in dotazioni:
        if not isinstance(dot, dict):
            continue
        label = dot.get("it", "")
        if not has_power and _has_keyword(label, KEYWORDS_POWER):
            has_power = True
        if not has_network and _has_keyword(label, KEYWORDS_NETWORK):
            has_network = True
        if has_power and has_network:
            break

    cur.execute(
        """
        UPDATE aula
        SET has_power_sockets   = %s,
            has_network_sockets = %s
        WHERE idaula = %s
        """,
        (has_power, has_network, idaula),
    )


# ==================================================================
# Worker
# ==================================================================

def process_aula(idaula: int) -> tuple[int, list[dict]]:
    dotazioni = fetch_dotazioni(idaula)
    time.sleep(REQUEST_DELAY)
    return idaula, dotazioni


# ==================================================================
# Main
# ==================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Scarica e importa le dotazioni delle aule Polimi.")
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=3,
        metavar="N",
        help="Thread paralleli per il download (default: 3)",
    )
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    idaule = load_idaule(conn)
    conn.close()

    if not idaule:
        log.warning("Nessuna aula trovata nel database.")
        return

    log.info("Aule da processare: %d  (workers: %d)", len(idaule), args.workers)

    risultati: list[tuple[int, list[dict]]] = []
    completate = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_aula, idaula): idaula for idaula in idaule}
        for future in as_completed(futures):
            risultati.append(future.result())
            completate += 1
            if completate % 10 == 0 or completate == len(idaule):
                log.info("Download: %d/%d aule", completate, len(idaule))

    # Trovo tutti i tipi distinti di dotazione
    tutti_i_tipi: dict[int, dict] = {}
    for _, dotazioni in risultati:
        for dot in dotazioni:
            if not isinstance(dot, dict):
                continue
            try:
                tid = int(dot["id"])
            except (KeyError, TypeError, ValueError):
                continue
            tutti_i_tipi[tid] = {"id": tid, "it": dot.get("it", ""), "en": dot.get("en", "")}

    log.info("Tipi dotazione distinti trovati: %d", len(tutti_i_tipi))

    # Import nel database
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            upsert_tipo_dotazioni(cur, tutti_i_tipi)

            for idaula, dotazioni in risultati:
                replace_aula_dotazioni(cur, idaula, dotazioni)
                update_aula_socket_flags(cur, idaula, dotazioni)

        conn.commit()
        log.info("Dotazioni importate con successo.")

    except Exception as exc:
        conn.rollback()
        log.exception("Errore durante l'import, rollback eseguito: %s", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
