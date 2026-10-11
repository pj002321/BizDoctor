# [역할] 설정 — 환경변수·경로·필터 기본값·신호등 기준·진단 TTL 등 상수를 한 곳에서 정한다.
# 환경변수를 읽기 위한 표준 모듈.
import os
# 파일 경로를 다루는 클래스.
from pathlib import Path
# .env 파일 내용을 환경변수로 불러오는 함수.
from dotenv import load_dotenv

# 이 파일 기준 두 단계 위 = ai-service/ 폴더를 기준 경로로 잡는다.
BASE_DIR = Path(__file__).resolve().parents[2]

# ai-service/.env 를 읽어 환경변수로 등록한다.
load_dotenv(BASE_DIR/".env")


# 문자열 환경변수를 읽는다. 비어 있으면 기본값.
def _env_str(key: str, default: str | None = None) -> str | None:
    """빈 값은 '없음' 으로 친다."""
    # 값이 없으면 빈 문자열로 바꾸고 앞뒤 공백을 지운다.
    raw = (os.getenv(key) or "").strip()
    # 빈 문자열이면 기본값을, 아니면 값을 돌려준다.
    return raw or default


# 정수 환경변수를 읽는다. 비어 있으면 기본값.
def _env_int(key: str, default: int) -> int:
    """빈 값은 '없음' 으로 친다 — `DB_POOL_SIZE=` 처럼 키만 남기면 int('') 가 터진다."""
    # 값이 없으면 빈 문자열로 바꾸고 공백을 지운다.
    raw = (os.getenv(key) or "").strip()
    # 값이 있으면 정수로 바꾸고, 없으면 기본값.
    return int(raw) if raw else default


# DB 주소를 SQLAlchemy 가 받아들이는 형식으로 맞춘다.
def _normalize_db_url(url: str | None) -> str | None:
    """어느 쪽을 붙여넣어도 돌게 맞춘다. SQLAlchemy 2.x 는 `postgres://` 를 거부한다."""
    # 주소가 없으면
    if not url:
        # None 을 돌려준다.
        return None
    # 공백과 양 끝의 따옴표를 지운다.
    url = url.strip().strip('"').strip("'")  # 따옴표째 붙여넣는 실수가 잦다
    # 두 가지 접두어 중 하나로 시작하면
    for prefix in ("postgres://", "postgresql://"):
        # 해당 접두어로 시작하는지 확인하고
        if url.startswith(prefix):
            # psycopg2 드라이버를 명시한 접두어로 바꿔 돌려준다.
            return "postgresql+psycopg2://" + url[len(prefix) :]
    # 그 외 형식은 그대로 돌려준다.
    return url


# 정리된 DB 접속 주소.
DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL"))

# OpenAI API 키(RAG 임베딩용).
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# 사용할 OpenAI 모델 이름.
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
# 임베딩 모델 이름.
EMBED_MODEL = "text-embedding-3-small"
# 임베딩 벡터 차원 수.
DIMENSION = 1536
# 토큰 수를 셀 때 쓰는 토크나이저 이름.
EMBED_TOKENIZER = "cl100k_base"
# 임베딩 한 번에 넣을 수 있는 최대 토큰 수.
EMBED_MAX_TOKENS = 8191
# 임베딩을 한 번에 몇 건씩 요청할지.
EMBED_BATCH_SIZE = _env_int("EMBED_BATCH_SIZE", 100)
# 데이터 폴더 경로(ai-service/data).
DATA_DIR = BASE_DIR / "data"

# --- DB 커넥션 풀 ---------------------------------------------------------
# 평소 유지할 DB 연결 수.
DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 5)
# 바쁠 때 추가로 열 수 있는 연결 수.
DB_MAX_OVERFLOW = _env_int("DB_MAX_OVERFLOW", 5)

# --- 내부망 호출 인증 (AGENTS.md: Next.js 서버만 X-Service-Token 으로 호출) ---
# 비어 있으면 검사하지 않는다 — 로컬 개발용. 배포 환경에서는 반드시 채운다.
SERVICE_TOKEN = _env_str("SERVICE_TOKEN")

# --- 상권 조회 (F-MAP) -----------------------------------------------------
# 최소 점포수 필터 기본값.
MIN_STORE_COUNT_DEFAULT = 5   # F-MAP-06 필터 기본값 — 폐업률 200~300% 이상치 차단
# '표본 적음' 배지 기준.
SMALL_SAMPLE_MAX_STORES = 5   # 점포 수가 이 값 이하인 셀에 "표본 적음" 배지 (스펙 6장 4번)
# 상권 신호등 색 기준 (F-MAP-01): risk_rank ≤0.60 GREEN / ≤0.85 YELLOW / 초과 RED.
# risk_rank 는 위험가중치(percentile 평균)를 같은 산업대분류 안에서 다시 순위로 바꾼 값이다.
# 위험가중치 평균에 이 기준을 그대로 쓰면 자치구 200개가 전부 GREEN 이 된다(평균이 0.5 근처에 몰림).
# → 'GREEN 하위 60% / YELLOW 다음 25% / RED 상위 15%'. 잠정값 — 팀 합의 후 기능정의서 F-MAP-01 갱신.
SIGNAL_LIGHT_GREEN_MAX = 0.60
# YELLOW 상한.
SIGNAL_LIGHT_YELLOW_MAX = 0.85
# 업종 랭킹에서 한 번에 돌려줄 수 있는 최대 개수.
INDUSTRY_RANK_TOP_N_MAX = 100

# --- 사업장 진단 (F-DIA) ---------------------------------------------------
# 정적 피처 기준 분기. 비우면 DB 의 최신 분기를 쓴다 — fact_panel 에 2025Q4 까지 있으므로 '2025 Q4 기준'(F-DIA-02).
FEATURE_BASE_QUARTER = _env_str("FEATURE_BASE_QUARTER")
# 업종이 KOSIS 산업에 매핑되지 않을 때 대신 쓸 값.
KOSIS_FALLBACK_INDUSTRY = "전산업"   # F-DIA-02 업종 미매핑 시 폴백
# 입력받는 월매출 개월 수.
SALES_MONTHS = 3                      # F-DIA-01 입력 개월 수
# 한 달 매출 입력 상한.
SALES_AMOUNT_MAX = 100_000_000_000    # 월 1,000억 원 — 오타(0 몇 개 더) 차단용 상한
# 비로그인 진단 결과 보관 시간(시간 단위).
DIAGNOSIS_TTL_HOURS = _env_int("DIAGNOSIS_TTL_HOURS", 24)  # F-DIA-08 비로그인 임시 토큰
