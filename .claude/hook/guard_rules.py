"""PostToolUse(Edit|Write) — 저장된 파일을 다시 읽어 절대 규칙 위반을 찾는다.

exit 2 + stderr 는 Claude 에게 그대로 전달된다. 편집은 이미 반영된 뒤라서
막는 게 아니라 "되돌려라"고 돌려보내는 방식이다. Edit 는 조각만 넘어오므로
파일 전체를 봐야 하는 규칙은 사후 검사가 유일한 자리다.
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

RISK_TYPES = ["정상_유지형", "단기_매출_정체형", "원가_상승_부담형",
              "매출_폭락형", "고금리_과다채무형", "상권_침체_붕괴형"]
# AGENTS.md "6개 risk_type" — 넷 중 하나만 고치면 build_signal_json 이 KeyError
RISK_TYPE_FILES = ("generate_synthetic_timeseries.py", "train_risk_model.py",
                   "rag_pipeline.py", "rag_documents.py")


def check(rel: str, text: str) -> list[str]:
    errs = []
    user_facing = rel.startswith(("src/", "ai-service/app/"))

    if user_facing and "예측력" in text:
        errs.append("[F-SYS-08] '예측력' 표기 금지 — 83.8% 는 시뮬레이션 규칙 복원율이다.")
    if re.search(r"(^|/)diagnosis/", rel) and "신호등" in text:
        errs.append("[F-SYS-01] 사업장 진단 코드에 '신호등' 금지 — '진단 등급' 으로 쓴다.")
    if re.search(r"(^|/)market/", rel) and "진단 등급" in text:
        errs.append("[F-SYS-01] 상권 코드에 '진단 등급' 금지 — 지역 결과는 '신호등' 이다.")

    # ponytail: '@/features/x' · '../features/x' 문자열만 본다. features 를 생략한
    # '../../x' 상대경로는 못 잡는다 — 잡아야 하면 biome 의 import 제한 규칙으로 옮긴다.
    m = re.match(r"src/features/([^/]+)/", rel)
    if m:
        others = set(re.findall(r"""['"](?:@/|(?:\.\./)+)features/([\w-]+)""", text)) - {m[1]}
        if others:
            errs.append(f"[구조] features 끼리 import 금지: {m[1]} → {sorted(others)}. "
                        "공용이면 src/shared 로 올린다.")

    if (rel.startswith("src/") and not rel.startswith("src/shared/supabase/")
            and "SERVICE_ROLE" in text):
        errs.append("[보안] service role 키는 src/shared/supabase/ (서버 전용) 에서만 읽는다.")
    if re.search(r"NEXT_PUBLIC_\w*(SERVICE_ROLE|SECRET|SERVICE_TOKEN|ANTHROPIC)", text):
        errs.append("[보안] 비밀값에 NEXT_PUBLIC_ 금지 — 브라우저 번들에 그대로 실린다.")

    if (rel.startswith(("ai-service/app/api/", "ai-service/app/schemas/"))
            and "_similarity_score" in text):
        errs.append("[F-RAG-04] _similarity_score 는 디버그 전용 — 응답 계약에 넣지 않는다.")

    # ponytail: 문자열 휴리스틱. 추론 코드에 'prior' 가 한 번도 안 나오면 잡는다.
    if rel.startswith("ai-service/app/") and ".predict(" in text and "prior" not in text:
        errs.append("[F-DIA-04] 모델 출력은 사전확률 보정(prior) 을 거쳐야 한다.")

    if rel.startswith("ai-service/") and rel.endswith(".py"):
        try:
            nodes = ast.walk(ast.parse(text))
        except SyntaxError:
            nodes = ()
        for n in nodes:
            if (isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "to_csv"
                    and not any(k.arg in ("encoding", None) for k in n.keywords)):
                errs.append(f"[인코딩] {n.lineno}행 to_csv 에 encoding=\"utf-8-sig\" 가 없다.")

    name = rel.rsplit("/", 1)[-1]
    if name == "join_kosis_hardship.py" and "last_region" not in text:
        errs.append("[KOSIS] 병합 셀 forward-fill(last_region) 을 지우면 서울이 전산업 한 행으로 준다.")
    if name == "generate_synthetic_timeseries.py" and "columns[6]" not in text:
        errs.append("[sgf] 부실사유코드는 위치(columns[6]) 로 고른다 — 헤더가 깨져 있다.")
    if name in RISK_TYPE_FILES:
        missing = [t for t in RISK_TYPES if t not in text]
        if missing:
            errs.append(f"[risk_type] {name} 에 빠진 유형: {missing}. 4개 파일을 같이 고친다.")
    return errs


def main() -> None:
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data["cwd"]).resolve()
    path = Path(data["tool_input"]["file_path"]).resolve()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return  # 프로젝트 밖 파일
    if not path.is_file():
        return
    errs = check(rel, path.read_text(encoding="utf-8", errors="ignore"))
    if errs:
        print(f"{rel} — 절대 규칙 위반:\n" + "\n".join(f"  {e}" for e in errs), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
