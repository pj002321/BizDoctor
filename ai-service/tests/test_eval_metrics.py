from eval.metrics import expired_shown, hit_at_k, reciprocal_rank

RETRIEVED = ["a", "b", "c"]

def test_hit_at_k():
    assert hit_at_k(RETRIEVED, ["c"])==1.0
    assert hit_at_k(RETRIEVED, ["c"], k=2)==0.0
    assert hit_at_k(RETRIEVED, ["z"])==0.0
    assert hit_at_k([], ["a"])==0.0


def test_reciprocal_rank():
    assert reciprocal_rank(RETRIEVED, ["a"]) == 1.0
    assert reciprocal_rank(RETRIEVED, ["b"]) == 0.5
    assert reciprocal_rank(RETRIEVED, ["c", "b"]) == 0.5   # 정답이 여럿이면 먼저 나온 것
    assert reciprocal_rank(RETRIEVED, ["z"]) == 0.0


def test_expired_shown():
    assert expired_shown(RETRIEVED, {"b"}) == 1.0
    assert expired_shown(RETRIEVED, {"z"}) == 0.0
    assert expired_shown([], {"b"}) == 0.0