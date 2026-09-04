#!/usr/bin/env bash
# The fixture is the repo's own seeded_defect.py; no second copy is kept.
set -euo pipefail
cp "$EVAL_REPO/.claude/hooks/tests/fixtures/seeded_defect.py" ./seeded_defect.py
