import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR/".env")


def _env_str(key: str, default: str | None = None) -> str | None:
    """빈 값은 '없음' 으로 친다."""
    raw = (os.getenv(key) or "").strip()
    return raw or default


def _env_int(key: str, default: int) -> int:
    """빈 값은 '없음' 으로 친다 — `DB_POOL_SIZE=` 처럼 키만 남기면 int('') 가 터진다."""
    raw = (os.getenv(key) or "").strip()
    return int(raw) if raw else default


def _normalize_db_url(url: str | None) -> str | None:
    """어느 쪽을 붙여넣어도 돌게 맞춘다. SQLAlchemy 2.x 는 `postgres://` 를 거부한다."""
    if not url:
        return None
    url = url.strip().strip('"').strip("'")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url


DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
EMBED_MODEL = "text-embedding-3-small"
DIMENSION = 1536
EMBED_TOKENIZER = "cl100k_base"
EMBED_MAX_TOKENS = 8191
EMBED_BATCH_SIZE = _env_int("EMBED_BATCH_SIZE", 100)
DATA_DIR = BASE_DIR / "data"

DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 5)
DB_MAX_OVERFLOW = _env_int("DB_MAX_OVERFLOW", 5)

SERVICE_TOKEN = _env_str("SERVICE_TOKEN")

MIN_STORE_COUNT_DEFAULT = 5
SMALL_SAMPLE_MAX_STORES = 5
SIGNAL_LIGHT_GREEN_MAX = 0.60
SIGNAL_LIGHT_YELLOW_MAX = 0.85
INDUSTRY_RANK_TOP_N_MAX = 100

FEATURE_BASE_QUARTER = _env_str("FEATURE_BASE_QUARTER")
KOSIS_FALLBACK_INDUSTRY = "전산업"
SALES_MONTHS = 3
SALES_AMOUNT_MAX = 100_000_000_000
DIAGNOSIS_TTL_HOURS = _env_int("DIAGNOSIS_TTL_HOURS", 24)
