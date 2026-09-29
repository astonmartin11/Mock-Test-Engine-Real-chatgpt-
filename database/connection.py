from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    """Return DATABASE_URL from the environment or Streamlit secrets."""
    value = os.getenv("DATABASE_URL")

    if value:
        return value

    # Streamlit Cloud stores secrets in st.secrets rather than .env.
    try:
        import streamlit as st  # imported lazily to keep this module reusable

        value = st.secrets.get("DATABASE_URL")
        if value:
            return str(value)
    except Exception:
        pass

    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Set it in .env for local development or Streamlit secrets in deployment."
    )


@contextmanager
def get_connection() -> Iterator[psycopg.Connection[Any]]:
    """Open a Neon PostgreSQL connection and close it safely."""
    conn = psycopg.connect(get_database_url())

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(
    query: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """Execute a query and return the first row as a dictionary."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)

            row = cur.fetchone()
            if row is None:
                return None

            columns = [desc.name for desc in cur.description]
            return dict(zip(columns, row))


def fetch_all(
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Execute a query and return rows as dictionaries."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)

            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]

            return [
                dict(zip(columns, row))
                for row in rows
            ]


def execute(
    query: str,
    params: tuple[Any, ...] = (),
) -> None:
    """Execute a write statement inside a transaction."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)


def execute_returning(
    query: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any]:
    """Execute INSERT/UPDATE ... RETURNING and return one row."""
    result = fetch_one(query, params)

    if result is None:
        raise RuntimeError("Expected a RETURNING row but received none.")

    return result


def check_connection() -> bool:
    """Return True when Neon is reachable and SELECT 1 succeeds."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return cur.fetchone() == (1,)
    except Exception:
        return False
