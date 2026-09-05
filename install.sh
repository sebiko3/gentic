#!/usr/bin/env bash
# Install this repo's Claude Code setup into ~/.claude (override with CLAUDE_HOME).
#
# Copies only files this repo TRACKS, and never removes anything else: ~/.claude also holds
# sessions, plugins, memory, and skills that belong to the user, not to this project. There is
# deliberately no rm -rf and no rsync --delete anywhere below.
#
# The file list comes from `git ls-files`, not from a filesystem walk. A walk would also pick up
# untracked files that happen to sit under .claude/ — in particular settings.local.json, which
# Claude Code writes to record project-scoped permission grants. Copying that into ~/.claude
# would silently promote those grants to machine scope.
#
#   ./install.sh           install or update
#   ./install.sh --check   report drift and exit non-zero if any; changes nothing

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO/.claude"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
CHECK=0

case "${1:-}" in
  --check) CHECK=1 ;;
  "")      ;;
  *) printf 'usage: %s [--check]\n' "$0" >&2; exit 2 ;;
esac

[ -d "$SRC" ] || { printf 'no .claude directory in %s\n' "$REPO" >&2; exit 2; }
if [ -e "$DEST" ] && [ ! -d "$DEST" ]; then
  printf 'destination is not a directory: %s\n' "$DEST" >&2
  exit 2
fi

# Tracked files under .claude/, minus anything that is machine state rather than repo content.
# settings.json and settings.local.json are never installed: they carry the user's theme,
# marketplaces, and permission grants.
list_sources() {
  if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$REPO" ls-files -z -- .claude | tr '\0' '\n' | sed "s|^|$REPO/|"
  else
    # Not a checkout (tarball install): fall back to an explicit allowlist of subtrees.
    find "$SRC" \( -path '*/agents/*' -o -path '*/commands/*' -o -path '*/hooks/*' \
      -o -path '*/skills/*' \) -type f
  fi | grep -v '/__pycache__/' | grep -v '\.pyc$' | grep -v '/settings\(\.local\)\?\.json$' | sort
}

changed=0
drift=()

while IFS= read -r file; do
  [ -f "$file" ] || continue
  rel="${file#"$SRC"/}"
  target="$DEST/$rel"

  if [ -f "$target" ] && cmp -s "$file" "$target"; then
    continue
  fi

  if [ "$CHECK" -eq 1 ]; then
    if [ -f "$target" ]; then drift+=("differs: $rel"); else drift+=("missing: $rel"); fi
    continue
  fi

  mkdir -p "$(dirname "$target")" || exit 1
  cp "$file" "$target" || exit 1
  [ -x "$file" ] && chmod +x "$target"
  printf '  update  %s\n' "$rel"
  changed=$((changed + 1))
done < <(list_sources)

if [ "$CHECK" -eq 1 ]; then
  if [ "${#drift[@]}" -gt 0 ]; then
    printf 'out of sync with %s:\n' "$DEST"
    printf '  %s\n' "${drift[@]}"
    printf '\nrun ./install.sh to sync\n'
    exit 1
  fi
  printf 'in sync with %s\n' "$DEST"
  exit 0
fi

printf '%d files changed in %s\n' "$changed" "$DEST"

# The installer never deletes, so an upgrade from a version that shipped a Stop hook leaves the
# old script on disk and its registration in settings.json — and the trimmed lib/common.py makes
# that script print a hook error at the end of every turn. Say exactly what to remove.
if [ -e "$DEST/hooks/stop.py" ] || grep -q '"Stop"' "$DEST/settings.json" 2>/dev/null; then
  cat <<NOTE

This setup no longer ships a Stop hook, but this machine still has stale pieces of one:
  - delete the "Stop" entry under "hooks" in $DEST/settings.json (back the file up first)
  - remove $DEST/hooks/stop.py and $DEST/hooks/lib/token_efficiency.py
  - remove $DEST/state if it exists (session state now lives in the brain)
Until then the old script runs at every turn end and reports a hook error.
NOTE
fi

# Copying the hook scripts does not activate them: Claude Code only runs hooks listed under the
# `hooks` key of settings.json. Saying nothing here would leave the whole layer — the routing
# frame, the destructive-command and .agentignore guards, the concurrency valve, the RED/GREEN
# ledger — silently inert. No Stop hook is shipped: nothing here ends a turn.
if ! grep -q '"hooks"' "$DEST/settings.json" 2>/dev/null; then
  cat <<'NOTE'

The hook scripts are installed but NOT registered, so they will not run yet.
settings.json is machine state and this installer never writes it. Add to
your settings.json (merging with what is already there):

  "hooks": {
    "SessionStart":    [{"matcher": "startup|resume",
                         "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/hooks/session_start.py\"",   "timeout": 10}]}],
    "UserPromptSubmit":[{"hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/hooks/user_prompt_submit.py\"", "timeout": 5}]}],
    "PreToolUse":      [{"matcher": "Bash|Read|Edit|Write|MultiEdit|NotebookEdit|NotebookRead|Task|Agent",
                         "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/hooks/pre_tool_use.py\"",   "timeout": 5}]}],
    "PostToolUse":     [{"matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit|Task|Agent",
                         "hooks": [{"type": "command", "command": "python3 \"$HOME/.claude/hooks/post_tool_use.py\"",  "timeout": 5}]}]
  }

Back the file up first. Verify with: bash .claude/hooks/tests/run.sh
NOTE
fi
