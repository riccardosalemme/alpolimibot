"""
pool.py – Connection pool PostgreSQL e context manager di transazione.
"""

import logging
import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

_DB_CONFIG = {
    "host":     os.getenv("PGHOST"),
    "port":     int(os.getenv("PGPORT", "5432")),
    "dbname":   os.getenv("PGDATABASE"),
    "user":     os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}

_pool: Optional[ThreadedConnectionPool] = None


def init_pool() -> None:
    global _pool
    _pool = ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        cursor_factory=psycopg2.extras.RealDictCursor,
        **_DB_CONFIG,
    )
    logging.info("Connection pool PostgreSQL inizializzato.")


def close_pool() -> None:
    if _pool:
        _pool.closeall()


@contextmanager
def get_conn():
    """Una connessione dal pool, con commit in uscita e rollback su eccezione."""
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
