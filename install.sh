#!/usr/bin/env bash
# Install this repo's Claude Code setup into ~/.claude (override with CLAUDE_HOME).
#
# Copies only the files this repo ships and never removes anything else: ~/.claude also holds
# sessions, plugins, memory, and skills that belong to the user, not to this project. There is
# deliberately no rm -rf and no rsync --delete anywhere below.
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

changed=0
drift=()

while IFS= read -r file; do
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
done < <(find "$SRC" -type f -not -path '*/__pycache__/*' -not -name '*.pyc' | sort)

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
