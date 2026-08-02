"""
Scarica le foto di tutte le aule visibili dal DB e le salva in
data/foto/aule/<idaula>.jpeg

Utilizzo:
    uv run jobs/spazi/3_foto.py
    uv run jobs/spazi/3_foto.py --output data/foto/aule
"""

import argparse
import logging
import os
from pathlib import Path

import psycopg2
import requests
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

DB_CONFIG = {
    "host":     os.getenv("PGHOST"),
    "port":     int(os.getenv("PGPORT", "5432")),
    "dbname":   os.getenv("PGDATABASE"),
    "user":     os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}


def fetch_aule_con_foto() -> list[dict]:
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT idaula, idfoto FROM aula WHERE idfoto IS NOT NULL"
            )
            return [{"idaula": row[0], "idfoto": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


def download_foto(idfoto: int, output_path: Path) -> bool:
    try:
        resp = requests.get(
            f"https://onlineservices.polimi.it/maps_rest/rest/syncro/rooms/foto/{idfoto}",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("HTTP %d per idfoto=%d", resp.status_code, idfoto)
            return False

        img_url = resp.text.strip()
        img_resp = requests.get(img_url, timeout=10)
        if img_resp.status_code != 200:
            log.warning("HTTP %d scaricando immagine per idfoto=%d", img_resp.status_code, idfoto)
            return False

        output_path.write_bytes(img_resp.content)
        return True

    except Exception as exc:
        log.error("Errore per idfoto=%d: %s", idfoto, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Scarica le foto delle aule visibili.")
    parser.add_argument(
        "--output", "-o",
        default="data/foto/aule",
        help="Cartella di output (default: data/foto/aule)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    aule = fetch_aule_con_foto()
    log.info("Trovate %d aule visibili con foto.", len(aule))

    ok = skipped = errors = 0
    for aula in aule:
        idaula = aula["idaula"]
        idfoto = aula["idfoto"]
        dest = output_dir / f"{idaula}.jpeg"

        if dest.exists():
            log.debug("Già presente: %s", dest)
            skipped += 1
            continue

        log.info("Scaricando idaula=%d idfoto=%d → %s", idaula, idfoto, dest)
        if download_foto(idfoto, dest):
            ok += 1
        else:
            errors += 1

    log.info("Completato: %d scaricate, %d già presenti, %d errori.", ok, skipped, errors)


if __name__ == "__main__":
    main()
