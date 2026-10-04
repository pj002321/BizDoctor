import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # 파이프라인(pipeline/)도 이 파일을 쓴다. 그쪽 venv 엔 python-dotenv 가 없을 수 있다.
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parents[2]

if load_dotenv is not None:
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
    url = url.strip().strip('"').strip("'")  # 따옴표째 붙여넣는 실수가 잦다
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

# --- 데이터 파이프라인 (pipeline/) ---------------------------------------
# 모든 파이프라인 스크립트는 시작할 때 os.chdir(DATA_DIR) 한다. 원본은 DATA_DIR/raw.

# 상권 신호등 색 기준 (F-MAP-01): 위험가중치 ≤0.60 GREEN / ≤0.85 YELLOW / 초과 RED
SIGNAL_LIGHT_GREEN_MAX = 0.60
SIGNAL_LIGHT_YELLOW_MAX = 0.85

# 행정동 × 산업 위험 가중치(risk_weights)에 넣을 최소 표본 (F-MAP-02)
REGION_RISK_MIN_OBS = 8        # 관측(업종 × 분기) 8건 이상
REGION_RISK_MIN_STORES = 100   # 전체 점포(유사_업종_점포_수) 합계 100 이상

# 업종별 폐업률 순위에 넣을 최소 관측 수 (F-MAP-05)
INDUSTRY_RANK_MIN_OBS = 200

# 행정표준코드 기준 서울 25개 자치구 (행정동_코드 앞 5자리 → 자치구명)
GU_CODE = {
    "11110": "종로구",   "11140": "중구",     "11170": "용산구",   "11200": "성동구",
    "11215": "광진구",   "11230": "동대문구", "11260": "중랑구",   "11290": "성북구",
    "11305": "강북구",   "11320": "도봉구",   "11350": "노원구",   "11380": "은평구",
    "11410": "서대문구", "11440": "마포구",   "11470": "양천구",   "11500": "강서구",
    "11530": "구로구",   "11545": "금천구",   "11560": "영등포구", "11590": "동작구",
    "11620": "관악구",   "11650": "서초구",   "11680": "강남구",   "11710": "송파구",
    "11740": "강동구",
}
