import os
from typing import Any

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        _engine = create_engine(url)
    return _engine


def query(sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a read-only query and return rows as dicts."""
    with _get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]
