#!/usr/bin/env bash
set -euo pipefail
cp "$EVAL_CASE_DIR/fixture/masterprompt.md" ./masterprompt.md
printf 'present\n' > present.txt
printf 'Two files.\n' > README.md
