#!/usr/bin/env bash
# Installs the exam harness. Run from the task workspace after:
#   git clone <this repo> .kit && bash .kit/install.sh
# Never touches Codex's config.toml. Safe to run more than once.
# Sub-agents are pinned to GPT-6.1-Sol (slug from the Codex 0.162 model catalog).
# Override with KIT_MODEL=<slug>, or KIT_MODEL=none to inherit the session's model.
set -euo pipefail

KIT_MODEL="${KIT_MODEL:-gpt-6.1-sol}"
[ "$KIT_MODEL" = "none" ] && KIT_MODEL=""

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$KIT/.." && pwd)"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
TS="$(date +%H%M%S)"

if [ "$(basename "$KIT")" != ".kit" ]; then
  echo "ERROR: clone into <workspace>/.kit (now: $KIT). The rules and skills refer to .kit/ paths." >&2
  exit 1
fi

echo "[1/5] Codex home: $CODEX_DIR"
mkdir -p "$CODEX_DIR/agents" "$CODEX_DIR/skills"

echo "[2/5] AGENTS.md rules block"
TARGET="$CODEX_DIR/AGENTS.md"
if [ -f "$TARGET" ]; then
  cp "$TARGET" "$TARGET.bak.$TS"
  # Drop an older copy of our block and trailing blank lines; keep everything else (including platform rules).
  awk '/<!-- workbench:begin -->/{skip=1; next} /<!-- workbench:end -->/{skip=0; next} skip{next}
       /^[[:space:]]*$/{blank++; next} {for(i=0;i<blank;i++) print ""; blank=0; print}' "$TARGET.bak.$TS" > "$TARGET"
  echo "  kept existing content (backup: $TARGET.bak.$TS)"
fi
if [ -s "$TARGET" ]; then echo >> "$TARGET"; fi
cat "$KIT/AGENTS.md" >> "$TARGET"

echo "[3/5] sub-agents and skills"
for f in "$KIT"/agents/*.toml; do
  dest="$CODEX_DIR/agents/$(basename "$f")"
  if [ -n "${KIT_MODEL:-}" ]; then
    awk -v m="$KIT_MODEL" 'NR==1{print; print "model = \"" m "\""; next} {print}' "$f" > "$dest"
  else
    cp "$f" "$dest"
  fi
  echo "  agent: $(basename "$f" .toml)${KIT_MODEL:+ (model=$KIT_MODEL)}"
done
for d in "$KIT"/skills/*/; do
  d="${d%/}"
  name="$(basename "$d")"
  rm -rf "${CODEX_DIR:?}/skills/$name"
  cp -R "$d" "$CODEX_DIR/skills/$name"
  echo "  skill: $name"
done

echo "[4/5] workspace files"
mkdir -p "$WS/process/specs" "$KIT/runtime"
for t in REQUIREMENTS NOTES HANDOFF; do
  if [ -f "$WS/process/$t.md" ]; then
    echo "  process/$t.md exists, kept"
  else
    cp "$KIT/templates/$t.md" "$WS/process/$t.md"
    echo "  process/$t.md created"
  fi
done
chmod +x "$KIT/cx" "$KIT"/tools/*.py 2>/dev/null || true

echo "[5/5] git"
if (cd "$WS" && git rev-parse --is-inside-work-tree >/dev/null 2>&1); then
  (
    cd "$WS"
    ex="$(git rev-parse --git-path info/exclude)"
    mkdir -p "$(dirname "$ex")"
    grep -qxF '.kit/' "$ex" 2>/dev/null || echo '.kit/' >> "$ex"
    git rev-parse HEAD > "$KIT/runtime/BASE_HEAD" 2>/dev/null || true
  )
  echo "  .kit/ hidden from git status/diff; process/ stays visible"
  echo "  HEAD recorded in .kit/runtime/BASE_HEAD (audit warns if it moves)"
else
  echo "  not a git repository, skipped"
fi

command -v python3 >/dev/null 2>&1 || echo "WARNING: python3 not found; .kit/tools will not run"

cat <<'EOF'

Done. Next:
  .kit/cx                 # codex with computer_use/browser_use disabled
  /status, /model         # confirm Sol 6.1 and effort
  then type: wb-kickoff 스킬로 시작해 (cards: .kit/cards/)
EOF
