"""훅 규칙 자체 점검. `python .claude/tests/test_hooks.py` — 조용하면 통과."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hook"))
from guard_git import check as git_check  # noqa: E402
from guard_rules import RISK_TYPES, check  # noqa: E402

ALL = " ".join(RISK_TYPES)

assert check("src/features/market/a.ts", "import x from '@/features/market/b'") == []
assert check("src/features/market/a.ts", "import x from '@/features/diagnosis/b'")
assert check("src/app/(app)/diagnosis/page.tsx", "사업장 신호등")
assert check("src/app/(app)/market/page.tsx", "지역 신호등") == []
assert check("ai-service/app/api/x.py", "정확도는 예측력")
assert check("docs/스펙.md", "예측력이라 표기하지 않는다") == []
assert check("src/features/x/a.ts", "process.env.SUPABASE_SERVICE_ROLE_KEY")
assert check("src/shared/supabase/server.ts", "process.env.SUPABASE_SERVICE_ROLE_KEY") == []
assert check(".env", "NEXT_PUBLIC_ANTHROPIC_API_KEY=")
assert check("ai-service/app/service/d.py", "p = model.predict(x)")
assert check("ai-service/app/service/d.py", "apply_prior(model.predict(x))") == []
assert check("ai-service/pipeline/a.py", "df.to_csv('a.csv', index=False)")
assert check("ai-service/pipeline/a.py", "df.to_csv('a.csv', encoding='utf-8-sig')") == []
assert check("ai-service/pipeline/prep/join_kosis_hardship.py", "x = 1")
assert check("ai-service/pipeline/train/train_risk_model.py", ALL) == []
assert check("ai-service/pipeline/doc/rag_pipeline.py", ALL.replace("매출_폭락형", ""))

assert git_check("git commit -m x", "production")
assert git_check("git commit -m x", "feature/architecture") == []
assert git_check("git push -f origin x", "feature/a")
assert git_check("git add .env.local", "feature/a")
assert git_check("git add AGENTS.md", "feature/a") == []
