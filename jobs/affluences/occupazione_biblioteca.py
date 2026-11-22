import logging
import os
from datetime import datetime

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

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

HEADERS = {
    'accept-language': 'en',
    'content-type': 'application/json',
    'host': 'api.affluences.com',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:150.0) Gecko/20100101 Firefox/150.0',
}

ANDROID_DEVICE_ID = os.getenv("ANDROID_DEVICE_ID", "12345678abcdefgh")
ANDROID_DEVICE_LANG = os.getenv("ANDROID_DEVICE_LANG", "en")
ANDROID_DEVICE_USER_AGENT = os.getenv("ANDROID_DEVICE_USER_AGENT", "Affluences/202606010 (Android; 15)")
ANDROID_APP_VERSION = os.getenv("ANDROID_APP_VERSION", "202606010")



def load_affluences_token():
    with open(".affluences_token", "r") as f:
        api_token = f.readline()
        if(len(api_token) != 36):
            log.error("Error reading .affluences_tokne. Content: %s", api_token)
            return None
        log.info("Affluences token loaded. %s", api_token)
        return api_token



def fetch_live_from_api(site_uuid: str, api_token: str) -> dict | None:
    url = f'https://api.affluences.com/app/v4/sites/{site_uuid}/live-data'
    headers = {
        "authorization": api_token,
        "user-agent": ANDROID_DEVICE_USER_AGENT,
        "accept-language": ANDROID_DEVICE_LANG,
        "accept-encoding": "gzip",
        "host": "api.affluences.com",
        "x-service-name": "mobile_app",
        "content-type": "application/json",
        "x-device-type": "android",
        "x-app-version": ANDROID_APP_VERSION,
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("Errore API per %s: %s", site_uuid, e)
        return None


def update_occupancies() -> None:
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, affluences_id, name FROM affluences_sites;")
        biblioteche = cur.fetchall()

        if not biblioteche:
            log.warning("Nessuna biblioteca trovata nel database.")
            return

        log.info("Inizio fetch per %d siti...", len(biblioteche))

        # Load app token
        api_token = load_affluences_token()
        if(not api_token):
            log.error("Can't load Affluences token.")
            return

        for b in biblioteche:
            raw_data = fetch_live_from_api(b['affluences_id'], api_token)

            if not raw_data:
                continue

            data_node = raw_data.get('data') or {}
            is_open = data_node.get('status', {}).get('isOpen')

            live_attendance = data_node.get('liveAttendance') or {}
            occupancy = live_attendance.get('occupancy')

            cur.execute("""
                INSERT INTO affluences_occupancies (site_id, is_open, occupancy_percent, fetched_at)
                VALUES (%s, %s, %s, %s);
            """, (b['id'], is_open, occupancy, datetime.now()))

            status_str = "Aperta" if is_open else "Chiusa"
            log.info("[%s] Stato: %s | Occupazione: %s%%", b['name'], status_str, occupancy)

        conn.commit()
        log.info("Aggiornamento completato alle %s", datetime.now().strftime('%H:%M:%S'))

    except Exception:
        log.exception("Errore generale durante l'aggiornamento")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    update_occupancies()


"""
SELECT * FROM public.affluences_occupancies
ORDER BY id ASC LIMIT 100;

SELECT DISTINCT ON (s.id)
    s.name,
    s.slug,
    o.occupancy_percent,
    o.is_open,
    o.fetched_at
FROM affluences_sites s
JOIN affluences_occupancies o ON s.id = o.site_id
ORDER BY s.id, o.fetched_at DESC;
"""
