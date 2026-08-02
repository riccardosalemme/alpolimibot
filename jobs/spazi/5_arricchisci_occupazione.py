"""
5_arricchisci_occupazione.py
============================
Arricchisce gli slot di occupazione nel DB con il nome del corso,
scaricando i dettagli di ogni aula dal portale servizi online.

Utilizzo:
    uv run jobs/spazi/5_arricchisci_occupazione.py                     # oggi
    uv run jobs/spazi/5_arricchisci_occupazione.py --giorni 7          # oggi + 6 giorni
    uv run jobs/spazi/5_arricchisci_occupazione.py --data 2026-03-16   # giorno specifico
    uv run jobs/spazi/5_arricchisci_occupazione.py --workers 4
"""

import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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

BASE_URL = "https://onlineservices.polimi.it/spazi/spazi/controller/Aula.do"
GRID_START_MINUTES = 8 * 60
SLOT_DURATION_MINUTES = 15
REQUEST_DELAY = 0.5

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def _slot_to_time(slot_index: int) -> str:
    total_minutes = GRID_START_MINUTES + slot_index * SLOT_DURATION_MINUTES
    h, m = divmod(total_minutes, 60)
    return f"{h:02d}:{m:02d}"


def _parse_schedule_row(row) -> dict | None:
    """Parsa una riga <tr class='normalRow'> della griglia occupazioni."""
    cells = row.find_all("td", recursive=False)
    if not cells:
        return None

    data_cell = row.find("td", class_="data")
    dove_cell = row.find("td", class_="dove")
    if not data_cell:
        return None

    parts = data_cell.get_text(strip=True).split()
    date_part = parts[-1] if parts else data_cell.get_text(strip=True)
    dove_str = dove_cell.get_text(strip=True) if dove_cell else ""

    grid_cells = [c for c in cells if c != data_cell and c != dove_cell]

    occupazioni = []
    slot_cursor = 0
    for cell in grid_cells:
        cls = " ".join(cell.get("class", []))
        colspan = int(cell.get("colspan", 1))
        if "slot" in cls:
            link = cell.find("a")
            corso = link.get_text(strip=True) if link else cell.get_text(strip=True)
            occupazioni.append({
                "corso": corso,
                "inizio": _slot_to_time(slot_cursor),
                "fine": _slot_to_time(slot_cursor + colspan),
            })
        slot_cursor += colspan

    return {"data": date_part, "aula": dove_str, "occupazioni": occupazioni}


def scrape_aula(idaula: int, from_date: date, to_date: date) -> list[dict]:
    """
    Scrape le occupazioni dell'aula nel range from_date..to_date.
    Restituisce la lista di dict {data, aula, occupazioni}.
    """
    session = requests.Session()
    session.headers.update(_HEADERS)

    resp = session.get(f"{BASE_URL}?evn_init=event&idaula={idaula}", timeout=15)
    resp.raise_for_status()
    jsessionid = session.cookies.get("JSESSIONID", "")

    form_data = {
        "spazi___model___formbean___DateOccupazForm___postBack": "true",
        "spazi___model___formbean___DateOccupazForm___formMode": "FILTER",
        "idaula": str(idaula),
        "spazi___model___formbean___DateOccupazForm___fromData_day": str(from_date.day),
        "spazi___model___formbean___DateOccupazForm___fromData_month": str(from_date.month),
        "spazi___model___formbean___DateOccupazForm___fromData_year": str(from_date.year),
        "jaf_spazi___model___formbean___DateOccupazForm___fromData_date_format": "dd/MM/yyyy",
        "spazi___model___formbean___DateOccupazForm___toData_day": str(to_date.day),
        "spazi___model___formbean___DateOccupazForm___toData_month": str(to_date.month),
        "spazi___model___formbean___DateOccupazForm___toData_year": str(to_date.year),
        "jaf_spazi___model___formbean___DateOccupazForm___toData_date_format": "dd/MM/yyyy",
        "evn_occupazioni": "Visualizza occupazioni",
    }

    post_url = BASE_URL
    if jsessionid:
        post_url += f";jsessionid={jsessionid}"
    post_url += "?jaf_currentWFID=main"

    resp = session.post(post_url, data=form_data, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    return [
        parsed
        for row in soup.find_all("tr", class_="normalRow")
        if (parsed := _parse_schedule_row(row))
    ]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def load_aule(conn, from_date: date, to_date: date) -> list[int]:
    """Restituisce gli idaula con dati di occupazione nel periodo."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT idaula
            FROM occupazione_giorno
            WHERE data BETWEEN %s AND %s
            ORDER BY idaula
            """,
            (from_date, to_date),
        )
        return [row[0] for row in cur.fetchall()]


def load_slots_db(conn, idaula: int, giorno: date) -> list[dict]:
    """Restituisce gli slot registrati nel DB per un'aula e un giorno."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT os.id, os.inizio::text, os.fine::text, os.corso
            FROM occupazione_slot os
            JOIN occupazione_giorno og ON og.id = os.id_giorno
            WHERE og.idaula = %s AND og.data = %s
            ORDER BY os.inizio
            """,
            (idaula, giorno),
        )
        return [
            {"id": r[0], "inizio": r[1][:5], "fine": r[2][:5], "corso": r[3]}
            for r in cur.fetchall()
        ]


# ---------------------------------------------------------------------------
# Logica per singola aula
# ---------------------------------------------------------------------------

def process_aula(idaula: int, from_date: date, to_date: date, db_config: dict) -> dict:
    """Scarica i corsi dall'HTML e aggiorna gli slot nel DB."""
    result = {"idaula": idaula, "aggiornati": 0, "senza_corso": 0, "errore": False}

    # 1. Scraping della pagina
    try:
        giorni_scraper = scrape_aula(idaula, from_date, to_date)
    except Exception as exc:
        log.warning("Aula %d: errore scraping — %s", idaula, exc)
        result["errore"] = True
        return result
    finally:
        time.sleep(REQUEST_DELAY)

    if not giorni_scraper:
        log.warning("Aula %d: 0 occupazioni dallo scraping", idaula)
        return result

    # Indicizza corsi scraped: {"GG/MM/AAAA": {"HH:MM": corso}}
    corsi_scraped: dict[str, dict[str, str]] = {}
    for g in giorni_scraper:
        mappa = {}
        for occ in g.get("occupazioni", []):
            if occ.get("corso"):
                mappa[occ["inizio"]] = occ["corso"]
        corsi_scraped[g["data"]] = mappa

    # 2. Query DB e aggiornamento corso per ogni slot
    conn = psycopg2.connect(**db_config)
    try:
        current = from_date
        while current <= to_date:
            chiave = current.strftime("%d/%m/%Y")
            corsi_giorno = corsi_scraped.get(chiave, {})
            slots_db = load_slots_db(conn, idaula, current)

            for slot in slots_db:
                corso_nuovo = corsi_giorno.get(slot["inizio"])
                if corso_nuovo:
                    if slot["corso"] != corso_nuovo:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE occupazione_slot SET corso = %s WHERE id = %s",
                                (corso_nuovo, slot["id"]),
                            )
                        result["aggiornati"] += 1
                elif not slot["corso"]:
                    result["senza_corso"] += 1

            current += timedelta(days=1)

        conn.commit()
    finally:
        conn.close()

    if result["senza_corso"] > 0:
        log.warning(
            "Aula %d: %d slot DB senza corso corrispondente dallo scraping",
            idaula, result["senza_corso"],
        )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Arricchisce gli slot di occupazione con il nome del corso."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--giorni", "-g", type=int, default=1, metavar="N",
        help="Numero di giorni a partire da oggi (default: 1 = solo oggi)",
    )
    group.add_argument(
        "--data", "-d", type=str, metavar="YYYY-MM-DD",
        help="Singolo giorno specifico",
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=2, metavar="N",
        help="Thread paralleli (default: 2)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.data:
        from_date = to_date = date.fromisoformat(args.data)
    else:
        from_date = date.today()
        to_date = from_date + timedelta(days=args.giorni - 1)

    log.info("Range: %s -> %s", from_date, to_date)

    # 1. Elenco aule
    conn = psycopg2.connect(**DB_CONFIG)
    aule = load_aule(conn, from_date, to_date)
    conn.close()
    log.info("Aule da processare: %d  (workers: %d)", len(aule), args.workers)

    if not aule:
        log.info("Nessuna aula con occupazione nel periodo.")
        return

    # 2. Per ogni aula: scraping + aggiornamento DB
    aggiornati_tot = senza_corso_tot = errori_tot = completate = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_aula, idaula, from_date, to_date, DB_CONFIG): idaula
            for idaula in aule
        }
        for future in as_completed(futures):
            r = future.result()
            aggiornati_tot += r["aggiornati"]
            senza_corso_tot += r["senza_corso"]
            errori_tot += int(r.get("errore", False))
            completate += 1
            if completate % 10 == 0 or completate == len(aule):
                log.info(
                    "Progresso: %d/%d aule | aggiornati: %d | senza corso: %d | errori: %d",
                    completate, len(aule), aggiornati_tot, senza_corso_tot, errori_tot,
                )

    log.info(
        "Completato — aggiornati: %d | senza corso: %d | errori scraping: %d",
        aggiornati_tot, senza_corso_tot, errori_tot,
    )


if __name__ == "__main__":
    main()
