"""검색 채점으로 검색 방식마다 점수 범위가 달라 doc_id 순서만으로 계산."""


def hit_at_k(returieved: list[str], gold: list[str], k: int = 3)->float:
    return float(any(d in gold for d in returieved[:k]))


def reciprocal_rank(retrieved: list[str], gold: list[str])->float:
    """처음 나온 정답의 순위의 역수 1위는 1 없다면 0 (RRF)"""
    for rank, d in enumerate(retrieved, 1):     # enumerate(...,1) - 순위를 1부터 센다.
        if d in gold:
            return 1 / rank
    return 0.0


def expired_shown(retrieved: list[str], expired: set[str])->float:
    """마감된 공고가 하나라도 섞인다면 1.0을 없다면 0.0을 반환"""
    return float(any(d in expired for d in retrieved))  # any() 반환 - True/False
    