import os
from typing import Any

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to your environment or .env file, "
                "e.g. DATABASE_URL=postgresql://user:pass@localhost:5432/dbname"
            )
        _engine = create_engine(url)
    return _engine


def query(sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a re