"""PreToolUse(Bash) — 되돌리기 힘든 git 조작을 실행 전에 막는다.

exit 2 면 명령이 실행되지 않고 stderr 가 Claude 에게 간다.
Claude 의 명령만 막는다. 사람이 터미널에서 치는 git 은 막지 못한다.
"""

import json
import os
import re
import subprocess
import sys

PROTECTED = {"development", "production"}  # AGENTS.md 형상 관리와 같게
SECRET = re.compile(r"\.env(\.\w+)?\.local|secrets/|serviceAccount")


def check(cmd: str, branch: str) -> list[str]:
    errs = []
    if re.search(r"\bgit\s+commit\b", cmd) and branch in PROTECTED:
        errs.append(f"[브랜치] {branch} 에 직접 커밋 금지 — feature/* 에서 작업한다.")
    if re.search(r"\bgit\s+push\b.*(--force\b|\s-f\b)", cmd):
        errs.append("[브랜치] force push 금지.")
    if re.search(r"\bgit\s+add\b", cmd) and SECRET.search(cmd):
        errs.append("[보안] 비밀 파일(.env.local · secrets/ · serviceAccount) 은 커밋하지 않는다.")
    return errs


def main() -> None:
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    cmd = data.get("tool_input", {}).get("command", "")
    if "git" not in cmd:
        return
    branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True,
        cwd=os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd"),
    ).stdout.strip()
    errs = check(cmd, branch)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
