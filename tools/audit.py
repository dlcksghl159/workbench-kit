#!/usr/bin/env python3
"""Pre-submit audit: scope, secrets, server binding, leftovers, syntax, docs, tests.

Prints PASS / WARN / FAIL lines and exits 1 if anything FAILs.
Standard library only; Python 3.8+.

Usage:
  python3 .kit/tools/audit.py [workspace] [--run-tests]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

SKIP_DIRS = {".git", ".kit", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", ".idea", ".vscode"}
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".json", ".yml", ".yaml", ".toml",
            ".ini", ".cfg", ".env", ".sh", ".md", ".txt", ".html", ".css", ".sql", ".java", ".go",
            ".rs", ".rb", ".php", ".ipynb", ".csv"}
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".sh", ".java", ".go", ".rb", ".php"}
DATA_EXT = {".csv", ".tsv", ".json", ".jsonl", ".xlsx", ".parquet"}
SECRET_PATTERNS = (
    ("OpenAI-style key", re.compile(r"\bsk-(proj-)?[A-Za-z0-9_-]{20,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Hardcoded credential", re.compile(
        r"""(?i)\b(api[_-]?key|secret[_-]?key|secret|password|passwd|access[_-]?token|token)\b["']?\s*[:=]\s*["'][^"'\s]{8,}["']""")),
)
LOCAL_BIND = (
    re.compile(r"""\bhost\s*=\s*["'](127\.0\.0\.1|localhost)["']"""),
    re.compile(r"""--host[ =]["']?(127\.0\.0\.1|localhost)\b"""),
    re.compile(r"""\.listen\(\s*\d+\s*,\s*["'](127\.0\.0\.1|localhost)["']"""),
    re.compile(r"""server\.address\s*=\s*["']?(127\.0\.0\.1|localhost)"""),
    re.compile(r"""\(\s*["'](127\.0\.0\.1|localhost)["']\s*,\s*\d{2,5}\s*\)"""),
)
RUN_WITHOUT_HOST = re.compile(r"\b(app\.run|uvicorn\.run)\((?![^)]*\bhost\b)[^)]*\)")
LEFTOVER = re.compile(r"\bbreakpoint\(\)|\bpdb\.set_trace\(\)|^\s*debugger;", re.MULTILINE)
TODO = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
SILENT_EXCEPT = re.compile(r"except(\s+(Exception|BaseException))?(\s+as\s+\w+)?\s*:\s*(#[^\n]*)?\n\s*pass\b")
RUN_HINT = re.compile(r"(python3?|uvicorn|flask|streamlit|npm|node|pnpm|yarn|java|go run|bash)\s+\S+")
MAX_SCAN_BYTES = 2 * 1024 * 1024

# Used when pytest is not installed: runs parameterless test_* functions and unittest cases.
MINI_RUNNER = r'''
import importlib.util, inspect, os, sys, unittest
sys.path.insert(0, os.getcwd())
passed = failed = skipped = 0
for path in sys.argv[1:]:
    folder = os.path.dirname(os.path.abspath(path))
    if folder not in sys.path:
        sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location("t_" + os.path.basename(path)[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:
        failed += 1
        print("IMPORT FAIL %s: %s: %s" % (path, type(exc).__name__, exc))
        continue
    for name, fn in sorted(vars(mod).items()):
        if name.startswith("test") and inspect.isfunction(fn) and fn.__module__ == mod.__name__:
            if inspect.signature(fn).parameters:
                skipped += 1
                continue
            try:
                fn()
                passed += 1
            except Exception as exc:
                failed += 1
                print("FAIL %s::%s %s: %s" % (path, name, type(exc).__name__, exc))
    suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    if suite.countTestCases():
        with open(os.devnull, "w") as sink:
            result = unittest.TextTestRunner(stream=sink).run(suite)
        failed += len(result.failures) + len(result.errors)
        passed += result.testsRun - len(result.failures) - len(result.errors)
print("mini-runner: %d passed, %d failed, %d skipped (fixtures need pytest)" % (passed, failed, skipped))
sys.exit(1 if failed else (0 if passed else 5))
'''

counts = {"PASS": 0, "WARN": 0, "FAIL": 0}


def emit(level, message):
    counts[level] = counts.get(level, 0) + 1
    print("%-4s %s" % (level, message))


def info(message):
    print("     " + message)


def run(cmd, cwd, timeout=60):
    try:
        out = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True, timeout=timeout)
        return out.returncode, out.stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


def rel(ws, path):
    return os.path.relpath(path, ws)


def walk_files(ws):
    for root, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield os.path.join(root, name)


def git_changes(ws):
    """Return (is_git, entries) where entries are (status, relpath)."""
    code, _ = run(["git", "rev-parse", "--is-inside-work-tree"], ws)
    if code != 0:
        return False, []
    base_file = os.path.join(ws, ".kit", "runtime", "BASE_HEAD")
    base = open(base_file).read().strip() if os.path.isfile(base_file) else ""
    entries = []
    if base:
        # Committed and uncommitted changes since install count as the submission's changes.
        _, diff = run(["git", "diff", "--name-status", base], ws)
        for line in diff.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and not parts[-1].startswith(".kit/"):
                entries.append((parts[0][0] + " ", parts[-1]))
    code, out = run(["git", "status", "--porcelain=v1", "-uall"], ws)
    for line in out.splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path.startswith(".kit/") or path == ".kit" or "__pycache__/" in path or path.endswith(".pyc"):
            continue
        if status == "??" or not any(p == path for _, p in entries):
            entries.append((status, path))
    return True, entries


def read_text(path):
    try:
        if os.path.getsize(path) > MAX_SCAN_BYTES:
            return None
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    if b"\x00" in raw[:4096]:
        return None
    for enc in ("utf-8", "cp949", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def mask(secret):
    return secret[:6] + "…" if len(secret) > 6 else "…"


def check_git(ws, is_git, entries):
    print("\n[1] 변경 범위")
    if not is_git:
        emit("WARN", "git 저장소가 아니라 변경 범위를 비교할 수 없어요. 전체 파일을 검사합니다.")
        return
    if not entries:
        emit("WARN", "변경된 파일이 없어요 (.kit 제외). 정말 제출할 게 맞나요?")
        return
    _, cached = run(["git", "diff", "--cached", "--name-only"], ws)
    staged = [p for p in cached.splitlines() if p and not p.startswith(".kit/")]
    deleted = [p for s, p in entries if "D" in s]
    untracked = [p for s, p in entries if s == "??" or s.startswith("A")]
    modified = [p for s, p in entries if s != "??" and not s.startswith("A") and "D" not in s]
    emit("PASS", "변경 %d개 (수정 %d, 새 파일 %d, 삭제 %d)" % (len(entries), len(modified), len(untracked), len(deleted)))
    for status, path in entries[:40]:
        info("%s %s" % (status, path))
    if len(entries) > 40:
        info("... %d more" % (len(entries) - 40))
    if staged:
        info("스테이징된 변경 %d개 (커밋하지 않으면 그대로 작업 트리에 남아요)" % len(staged))
    if deleted:
        emit("WARN", "삭제된 추적 파일: %s — 의도한 건가요?" % ", ".join(deleted[:5]))
    data_touched = [p for p in modified if os.path.splitext(p)[1].lower() in DATA_EXT]
    if data_touched:
        emit("WARN", "원본 데이터로 보이는 파일이 수정됐어요: %s" % ", ".join(data_touched[:5]))
    base_file = os.path.join(ws, ".kit", "runtime", "BASE_HEAD")
    if os.path.isfile(base_file):
        with open(base_file) as fh:
            base = fh.read().strip()
        _, head = run(["git", "rev-parse", "HEAD"], ws)
        head = head.strip()
        if base and head and head != base:
            is_ancestor, _ = run(["git", "merge-base", "--is-ancestor", base, head], ws)
            if is_ancestor == 0:
                _, n = run(["git", "rev-list", "--count", "%s..%s" % (base, head)], ws)
                emit("PASS", "설치 이후 커밋 %s개, 원래 이력은 그대로예요" % n.strip())
            else:
                emit("WARN", "설치 시점 커밋(%s)이 현재 이력에 없어요. reset/rebase/amend로 이력이 바뀌었는지 확인하세요." % base[:8])
        else:
            emit("PASS", "이력 변화 없음 (설치 시점 HEAD 그대로)")


def target_files(ws, is_git, entries):
    if is_git:
        paths = [os.path.join(ws, p) for s, p in entries if "D" not in s]
        return [p for p in paths if os.path.isfile(p)]
    return list(walk_files(ws))


def check_content(ws, files):
    print("\n[2] 내용 검사 (비밀값, 바인딩, 남은 디버그 코드)")
    secrets, binds, leftovers, todos, silent, big = [], [], [], [], [], []
    for path in files:
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size > 5 * 1024 * 1024:
            big.append("%s (%.1f MB)" % (rel(ws, path), size / 1048576.0))
        ext = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        if ext not in TEXT_EXT and not name.startswith(".env"):
            continue
        text = read_text(path)
        if text is None:
            continue
        r = rel(ws, path)
        for label, rx in SECRET_PATTERNS:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                secrets.append("%s:%d %s %s" % (r, line, label, mask(m.group(0))))
        if ext in CODE_EXT or ext == ".py":
            for rx in LOCAL_BIND:
                for m in rx.finditer(text):
                    binds.append("%s:%d %s" % (r, text.count("\n", 0, m.start()) + 1, m.group(0)))
            for m in RUN_WITHOUT_HOST.finditer(text):
                binds.append("%s:%d %s (host 미지정 → 127.0.0.1)" % (r, text.count("\n", 0, m.start()) + 1, m.group(0)[:60]))
            for m in LEFTOVER.finditer(text):
                leftovers.append("%s:%d %s" % (r, text.count("\n", 0, m.start()) + 1, m.group(0).strip()))
            n_todo = len(TODO.findall(text))
            if n_todo:
                todos.append("%s (%d)" % (r, n_todo))
            if ext == ".py":
                for m in SILENT_EXCEPT.finditer(text):
                    silent.append("%s:%d" % (r, text.count("\n", 0, m.start()) + 1))
    if secrets:
        emit("FAIL", "비밀값으로 보이는 문자열 %d건" % len(secrets))
        for s in secrets[:10]:
            info(s)
    else:
        emit("PASS", "비밀값 패턴 없음")
    if binds:
        emit("WARN", "localhost 바인딩 의심 %d건 — 내장 브라우저 미리보기는 0.0.0.0이어야 연결돼요" % len(binds))
        for b in binds[:8]:
            info(b)
    else:
        emit("PASS", "localhost 바인딩 패턴 없음")
    if leftovers:
        emit("FAIL", "디버그 중단점이 남아 있어요")
        for x in leftovers[:8]:
            info(x)
    if silent:
        emit("WARN", "예외를 조용히 삼키는 코드 (except: pass) %d곳: %s" % (len(silent), ", ".join(silent[:5])))
    if todos:
        emit("WARN", "TODO/FIXME 남음: %s" % ", ".join(todos[:6]))
    if big:
        emit("WARN", "5MB 넘는 파일: %s" % ", ".join(big[:5]))


def check_syntax(ws, files):
    print("\n[3] 문법 검사")
    errors, checked = [], 0
    node = shutil.which("node")
    for path in files:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".py":
            text = read_text(path)
            if text is None:
                continue
            checked += 1
            try:
                compile(text, path, "exec")
            except SyntaxError as exc:
                errors.append("%s:%s %s" % (rel(ws, path), exc.lineno, exc.msg))
        elif ext in (".js", ".mjs", ".cjs") and node:
            checked += 1
            code, out = run([node, "--check", path], ws)
            if code != 0:
                errors.append("%s %s" % (rel(ws, path), out.strip().splitlines()[-1] if out.strip() else ""))
    if errors:
        emit("FAIL", "문법 오류 %d건" % len(errors))
        for e in errors[:10]:
            info(e)
    elif checked:
        emit("PASS", "문법 검사 통과 (%d개 파일)" % checked)
    else:
        info("검사할 .py/.js 변경 파일 없음")


def find_tests(ws):
    found = []
    for path in walk_files(ws):
        name = os.path.basename(path)
        r = rel(ws, path)
        if (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py") \
                or re.search(r"\.(test|spec)\.(js|ts|jsx|tsx)$", name):
            found.append(r)
    return found


def check_docs(ws):
    print("\n[4] 문서와 테스트")
    req = read_text(os.path.join(ws, "process", "REQUIREMENTS.md")) or ""
    rids = sorted(set(re.findall(r"\|\s*(R\d+)\s*\|\s*(?:Must|Should|Could)\s*\|\s*[^|\s][^|]*\|", req)))
    if rids:
        emit("PASS", "요구사항 %d개 (%s)" % (len(rids), ", ".join(rids[:12])))
    else:
        emit("WARN", "process/REQUIREMENTS.md에 채워진 R-id 행이 없어요")
    notes = read_text(os.path.join(ws, "process", "NOTES.md")) or ""
    verify = notes.split("## 검증 기록", 1)[1] if "## 검증 기록" in notes else ""
    verify_lines = [l for l in verify.splitlines() if l.strip() and not l.strip().startswith("<!--")]
    if verify_lines:
        emit("PASS", "검증 기록 %d줄" % len(verify_lines))
    else:
        emit("WARN", "NOTES.md '검증 기록'이 비어 있어요 — 실행한 검증 명령과 결과를 남기세요")
    report_text = read_text(os.path.join(ws, "process", "REPORT.md"))
    readme_text = read_text(os.path.join(ws, "README.md")) or ""
    if report_text is None:
        emit("WARN", "process/REPORT.md가 없어요 (과제가 따로 요구한 보고서가 있으면 무시)")
    elif re.search(r"\|\s*R1\s*\|\s*\|", report_text) or "file:function" in report_text:
        emit("WARN", "REPORT.md에 템플릿 빈칸이 남아 있어요")
    else:
        emit("PASS", "REPORT.md 작성됨")
    if RUN_HINT.search((report_text or "") + "\n" + readme_text):
        emit("PASS", "실행 방법이 문서에 있어요")
    else:
        emit("WARN", "README나 REPORT에서 실행 명령을 찾지 못했어요")
    tests = find_tests(ws)
    if tests:
        emit("PASS", "테스트 파일 %d개: %s" % (len(tests), ", ".join(tests[:5])))
        rid_named = [t for t in tests if re.search(r"R\d+", t)]
        if not rid_named:
            text = "".join(read_text(os.path.join(ws, t)) or "" for t in tests[:20])
            if not re.search(r"def test_R\d+|test\(['\"]R\d+|it\(['\"]R\d+", text):
                emit("WARN", "테스트 이름에 R-id가 안 보여요 (요구사항 추적이 약해져요)")
    else:
        emit("WARN", "테스트 파일을 찾지 못했어요")
    return tests


def run_tests(ws, tests):
    print("\n[5] 테스트 실행")
    py_tests = [t for t in tests if t.endswith(".py")]
    if py_tests:
        has_pytest, _ = run([sys.executable, "-c", "import pytest"], ws)
        if has_pytest == 0:
            label, cmd = "pytest -q", [sys.executable, "-m", "pytest", "-q"]
        else:
            label, cmd = "mini-runner (pytest 없음)", [sys.executable, "-c", MINI_RUNNER] + py_tests
        code, out = run(cmd, ws, timeout=600)
        if code == 5:
            emit("WARN", "%s → 실행된 테스트 0개" % label)
        else:
            emit("PASS" if code == 0 else "FAIL", "%s → exit %d" % (label, code))
        for line in out.strip().splitlines()[-6:]:
            info(line)
    elif os.path.isfile(os.path.join(ws, "package.json")) and shutil.which("npm"):
        code, out = run(["npm", "test", "--silent"], ws, timeout=600)
        emit("PASS" if code == 0 else "FAIL", "npm test → exit %d" % code)
        for line in out.strip().splitlines()[-6:]:
            info(line)
    else:
        info("실행할 테스트를 찾지 못했어요")


def check_ports():
    print("\n[6] 떠 있는 서버")
    lines = []
    if shutil.which("ss"):
        _, out = run(["ss", "-ltn"], ".")
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                lines.append(parts[3])
    elif shutil.which("lsof"):
        _, out = run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], ".")
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 9:
                lines.append(parts[8])
    shown = 0
    for addr in sorted(set(lines)):
        port = addr.rsplit(":", 1)[-1]
        if not port.isdigit() or not (1024 <= int(port) <= 9999):
            continue
        local = addr.startswith("127.") or addr.startswith("[::1]") or addr.startswith("localhost")
        info("%s%s" % (addr, "  ← localhost 전용 (미리보기 연결 안 됨)" if local else ""))
        shown += 1
    if not shown:
        info("1024-9999 포트에서 대기 중인 서버 없음")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workspace", nargs="?", default=".")
    parser.add_argument("--run-tests", action="store_true", help="run pytest/unittest or npm test")
    parser.add_argument("--all", action="store_true", help="scan every file, not only changed ones (baseline sweep of provided code)")
    args = parser.parse_args()
    ws = os.path.abspath(args.workspace)
    print("audit: %s" % ws)
    is_git, entries = git_changes(ws)
    check_git(ws, is_git, entries)
    files = list(walk_files(ws)) if args.all else target_files(ws, is_git, entries)
    if args.all:
        print("(--all: 제공된 코드 전체를 검사합니다)")
    check_content(ws, files)
    check_syntax(ws, files)
    tests = check_docs(ws)
    if args.run_tests:
        run_tests(ws, tests)
    check_ports()
    print("\n결과: FAIL %d / WARN %d / PASS %d" % (counts["FAIL"], counts["WARN"], counts["PASS"]))
    print("제출 전 직접 확인: 에디터 탭 전부 '저장됨' · 데모 서버 상태 · 확인 문제 대비 노트 읽기")
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
