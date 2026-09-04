#!/usr/bin/env bash
# Fresh copy of the admin dashboard fixture, the real gentic CLAUDE.md (so the routing text is
# never a stale copy), and one initial commit so the run starts on a clean tree.
set -euo pipefail
cp -R "$EVAL_CASE_DIR/fixture/." .
cp "$EVAL_REPO/CLAUDE.md" ./CLAUDE.md
git init -q
git add -A
git -c user.name=eval -c user.email=eval@example.com commit -qm "init" >/dev/null
