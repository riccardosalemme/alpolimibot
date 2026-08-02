"""
Scarica il dataset principale degli spazi dal portale Polimi e importa
polo, sede, campus, edificio, piano e aula nel database PostgreSQL.

"""

import logging
import os
from datetime import datetime

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


# ==================================================================
# Helpers
# ==================================================================

def fetch_json(url: str) -> dict | list | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            log.error("HTTP %d per %s", resp.status_code, url)
            return None
        return resp.json()
    except Exception as exc:
        log.error("Errore richiesta %s: %s", url, exc)
        return None


def _int_or_none(value) -> int | None:
    """Converte in int, ignorando il valore sentinella -2147483648."""
    if value is None:
        return None
    try:
        v = int(value)
        return None if v == -2147483648 else v
    except (ValueError, TypeError):
        return None


def _ts_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    log.warning("Formato data non riconosciuto: %s", value)
    return None


# ==================================================================
# Insert helpers
# ==================================================================

def insert_polo(cur, polo_list: list) -> None:
    log.info("Inserimento %d polo…", len(polo_list))
    rows = [(p["csim"], p["nome"], p.get("visibile", "S")) for p in polo_list]
    execute_values(
        cur,
        """
        INSERT INTO polo (csim, nome, visibile)
        VALUES %s
        ON CONFLICT (csim) DO UPDATE
            SET nome     = EXCLUDED.nome,
                visibile = EXCLUDED.visibile
        """,
        rows,
    )


def insert_sede(cur, sede_list: list) -> None:
    log.info("Inserimento %d sedi…", len(sede_list))
    rows = [(s["csis"], s["csim"], s["nome"], s.get("visibile", "S")) for s in sede_list]
    execute_values(
        cur,
        """
        INSERT INTO sede (csis, csim, nome, visibile)
        VALUES %s
        ON CONFLICT (csis) DO UPDATE
            SET csim     = EXCLUDED.csim,
                nome     = EXCLUDED.nome,
                visibile = EXCLUDED.visibile
        """,
        rows,
    )


def insert_campus(cur, campus_list: list) -> None:
    log.info("Inserimento %d campus…", len(campus_list))
    rows = [(c["csic"], c["csis"], c["nome"], c.get("visibile", "S")) for c in campus_list]
    execute_values(
        cur,
        """
        INSERT INTO campus (csic, csis, nome, visibile)
        VALUES %s
        ON CONFLICT (csic) DO UPDATE
            SET csis     = EXCLUDED.csis,
                nome     = EXCLUDED.nome,
                visibile = EXCLUDED.visibile
        """,
        rows,
    )


def insert_edifici(cur, edificio_list: list) -> None:
    log.info("Inserimento %d edifici…", len(edificio_list))
    rows = []
    for e in edificio_list:
        rows.append((
            e["csie"],
            e["csic"],
            e["nome"],
            _int_or_none(e.get("idEdificio")),
            _int_or_none(e.get("idCampus")),
            e.get("indirizzo"),
            e.get("cap"),
            e.get("provincia"),
            e.get("cittaEdificio"),
            e.get("nomeStorico"),
            # e.get("enteGestore"), è sempre il poli, scritto in 3 forme diverse
            e.get("enteProprietario"),
            e.get("titoloGodimento"),
            e.get("noteAccessoDisabili"),
            e.get("noteAccesso"),
            e.get("prefissoToponomastico"),
            e.get("numeroCivico"),
            # e.get("etichettaMappa"),
            e.get("visibile", "S"),
            _int_or_none(e.get("annoCostruzione")),
            _int_or_none(e.get("annoAttivazione")),
        ))
    execute_values(
        cur,
        """
        INSERT INTO edificio (
            csie, csic, nome, id_edificio, id_campus, indirizzo, cap, provincia,
            citta_edificio, nome_storico, ente_proprietario,
            titolo_godimento, note_accesso_disabili, note_accesso,
            prefisso_toponomastico, numero_civico, visibile,
            anno_costruzione, anno_attivazione
        ) VALUES %s
        ON CONFLICT (csie) DO UPDATE
            SET csic                   = EXCLUDED.csic,
                nome                   = EXCLUDED.nome,
                id_edificio            = EXCLUDED.id_edificio,
                id_campus              = EXCLUDED.id_campus,
                indirizzo              = EXCLUDED.indirizzo,
                cap                    = EXCLUDED.cap,
                provincia              = EXCLUDED.provincia,
                citta_edificio         = EXCLUDED.citta_edificio,
                nome_storico           = EXCLUDED.nome_storico,
                ente_proprietario      = EXCLUDED.ente_proprietario,
                titolo_godimento       = EXCLUDED.titolo_godimento,
                note_accesso_disabili  = EXCLUDED.note_accesso_disabili,
                note_accesso           = EXCLUDED.note_accesso,
                prefisso_toponomastico = EXCLUDED.prefisso_toponomastico,
                numero_civico          = EXCLUDED.numero_civico,
                visibile               = EXCLUDED.visibile,
                anno_costruzione       = EXCLUDED.anno_costruzione,
                anno_attivazione       = EXCLUDED.anno_attivazione
        """,
        rows,
    )


def insert_piani(cur, piano_list: list) -> None:
    log.info("Inserimento %d piani…", len(piano_list))
    rows = [
        (p["csip"], p["csie"], p["nome"], _int_or_none(p.get("n")), p.get("visibile", "S"))
        for p in piano_list
    ]
    execute_values(
        cur,
        """
        INSERT INTO piano (csip, csie, nome, n, visibile)
        VALUES %s
        ON CONFLICT (csip) DO UPDATE
            SET csie     = EXCLUDED.csie,
                nome     = EXCLUDED.nome,
                n        = EXCLUDED.n,
                visibile = EXCLUDED.visibile
        """,
        rows,
    )


def insert_aule(cur, aula_list: list, csie_to_csis: dict[str, str]) -> None:
    log.info("Inserimento %d aule…", len(aula_list))
    rows = []
    for a in aula_list:
        csie = a.get("csie") or None
        csis = csie_to_csis.get(csie) if csie else None
        rows.append((
            int(a["idaula"]),
            a.get("sigla"),
            a.get("csiv"),
            a.get("csip") or None,
            csie,
            csis,
            _int_or_none(a.get("idVano")),
            # handle        → sempre null, non inserito
            a.get("esterna"),
            a.get("indir_esterna"),
            a.get("ubicazione_esterna"),
            # c_istituto    → 0 o null, poco rilevante, non inserito
            # tipo_istituto → sempre null, non inserito
            a.get("note"),
            a.get("uso_test"),
            # fittizia      → sempre 'N', non inserita
            # conferma_ate  → sempre 'S', non inserita
            _int_or_none(a.get("capienza_ate")),
            a.get("morfologia"),
            _int_or_none(a.get("posti_disabili")),
            _int_or_none(a.get("idfoto")),
            # datafoto      → sempre null, non inserita
            _int_or_none(a.get("numero_postazioni_attive")),
            _int_or_none(a.get("capienza")),
            a.get("competenza"),
            # denominazione → compilata solo per aule 'A.' ed è uguale a sigla, non inserita
            a.get("categoria"),
            a.get("tipologia"),
            _ts_or_none(a.get("attivazione")),
            # disattivazione → sempre null (previsto per uso futuro), non inserita
            _int_or_none(a.get("numero_postazioni")),
            # tipo_postazioni → sempre null, non inserito
            a.get("descrizione"),
        ))
    execute_values(
        cur,
        """
        INSERT INTO aula (
            idaula, sigla, csiv, csip, csie, csis, id_vano,
            esterna, indir_esterna, ubicazione_esterna,
            note, uso_test,
            capienza_ate, morfologia, posti_disabili, idfoto,
            numero_postazioni_attive, capienza, competenza,
            categoria, tipologia, attivazione,
            numero_postazioni, descrizione
        ) VALUES %s
        ON CONFLICT (idaula) DO UPDATE
            SET sigla                    = EXCLUDED.sigla,
                csiv                     = EXCLUDED.csiv,
                csip                     = EXCLUDED.csip,
                csie                     = EXCLUDED.csie,
                csis                     = EXCLUDED.csis,
                id_vano                  = EXCLUDED.id_vano,
                esterna                  = EXCLUDED.esterna,
                indir_esterna            = EXCLUDED.indir_esterna,
                ubicazione_esterna       = EXCLUDED.ubicazione_esterna,
                note                     = EXCLUDED.note,
                uso_test                 = EXCLUDED.uso_test,
                capienza_ate             = EXCLUDED.capienza_ate,
                morfologia               = EXCLUDED.morfologia,
                posti_disabili           = EXCLUDED.posti_disabili,
                idfoto                   = EXCLUDED.idfoto,
                numero_postazioni_attive = EXCLUDED.numero_postazioni_attive,
                capienza                 = EXCLUDED.capienza,
                competenza               = EXCLUDED.competenza,
                categoria                = EXCLUDED.categoria,
                tipologia                = EXCLUDED.tipologia,
                attivazione              = EXCLUDED.attivazione,
                numero_postazioni        = EXCLUDED.numero_postazioni,
                descrizione              = EXCLUDED.descrizione
        """,
        rows,
    )


# ==================================================================
# Main
# ==================================================================

def main() -> None:
    log.info("Scaricamento dataset spazi Polimi…")
    data = fetch_json(f"{BASE_URL}/spazi/")
    if not data:
        raise RuntimeError("Impossibile scaricare il dataset principale.")

    log.info(
        "Trovati: %d polo, %d sede, %d campus, %d edifici, %d piani, %d aule",
        len(data.get("polo", [])),
        len(data.get("sede", [])),
        len(data.get("campus", [])),
        len(data.get("edificio", [])),
        len(data.get("piano", [])),
        len(data.get("aula", [])),
    )

    log.info(f"Connessione al database {DB_CONFIG['user']} @ {DB_CONFIG['host']} : {DB_CONFIG['port']} / {DB_CONFIG['dbname']} ...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # Rispetta l'ordine delle FK: polo → sede → campus → edificio → piano → aula
            insert_polo(cur,     data.get("polo",     []))
            insert_sede(cur,     data.get("sede",     []))
            insert_campus(cur,   data.get("campus",   []))
            insert_edifici(cur,  data.get("edificio", []))
            insert_piani(cur,    data.get("piano",    []))

            # Mappa csie → csis: aula.csie → edificio.csic → campus.csis
            # Questo mi permette di non dover fare due join ogni volta che cerco un'aula
            csic_to_csis = {c["csic"]: c["csis"] for c in data.get("campus", [])}
            csie_to_csis = {e["csie"]: csic_to_csis.get(e["csic"]) for e in data.get("edificio", [])}
            insert_aule(cur,     data.get("aula",     []), csie_to_csis)

        conn.commit()
        log.info("Spazi scaricati e importati con successo.")

    except Exception as exc:
        conn.rollback()
        log.exception("Errore durante l'import, rollback eseguito: %s", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
