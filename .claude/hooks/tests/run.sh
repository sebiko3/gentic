#!/usr/bin/env bash
# Harness for the machine-wide hooks. Runs without restarting Claude Code.
# Exit 0 and no FAIL lines means every hook is behaving.

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILURES=0

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }
pass() { printf '  ok    %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

section "Unit and contract suites"
for suite in test_lib test_classifier test_gate test_guard_and_session test_agentignore test_install test_structure test_review_nudge; do
  if out=$(cd "$HOOKS" && python3 "tests/$suite.py" 2>&1); then
    pass "$suite ($(printf '%s' "$out" | grep -oE 'Ran [0-9]+ tests' | head -1))"
  else
    fail "$suite"
    printf '%s\n' "$out" | tail -20
  fi
done

section "Degradation: every hook survives hostile input"
for script in user_prompt_submit post_tool_use stop session_start pre_tool_use; do
  for payload in '' '{not json' '{}' '[]' 'null'; do
    err=$(printf '%s' "$payload" | python3 "$HOOKS/$script.py" 2>&1 >/dev/null)
    code=$?
    if [ $code -ne 0 ] || printf '%s' "$err" | grep -q Traceback; then
      fail "$script rejected payload: ${payload:-<empty>} (exit $code)"
    fi
  done
done
[ $FAILURES -eq 0 ] && pass "5 hooks x 5 hostile payloads exit 0 cleanly"

section "Degradation: no git repository"
TMP=$(mktemp -d)
for script in user_prompt_submit session_start; do
  err=$(printf '{"cwd":"%s","prompt":"refactor every service to use the new secure token store","session_id":"h"}' "$TMP" \
        | python3 "$HOOKS/$script.py" 2>&1 >/dev/null)
  if [ $? -ne 0 ] || printf '%s' "$err" | grep -q Traceback; then
    fail "$script failed outside a git repo"
  else
    pass "$script no-ops outside a git repo"
  fi
done
rmdir "$TMP" 2>/dev/null

section "Latency budget (UserPromptSubmit, median of 20)"
MEDIAN=$(cd "$HOOKS" && python3 - <<'PY'
import json, statistics, subprocess, sys, tempfile, time
payload = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "bench",
                      "prompt": "refactor every service to use the new secure token store",
                      "cwd": tempfile.gettempdir()})
times = []
for _ in range(20):
    start = time.perf_counter()
    subprocess.run([sys.executable, "user_prompt_submit.py"], input=payload,
                   capture_output=True, text=True)
    times.append((time.perf_counter() - start) * 1000)
print(f"{statistics.median(times):.1f}")
PY
)
if awk "BEGIN{exit !($MEDIAN < 150)}"; then pass "median ${MEDIAN}ms < 150ms"; else fail "median ${MEDIAN}ms exceeds 150ms"; fi

section "Latency budget (PreToolUse with .agentignore, median of 20)"
PRE_MEDIAN=$(cd "$HOOKS" && python3 - <<'PY'
import json, statistics, subprocess, sys, tempfile, time
from pathlib import Path
root = tempfile.mkdtemp()
(Path(root) / ".git").mkdir()
(Path(root) / ".agentignore").write_text("secrets/\n*.pem\n\n[read-only]\nvendor/\n")
(Path(root) / "src").mkdir()
(Path(root) / "src" / "app.py").write_text("x")
payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read",
                      "tool_input": {"file_path": f"{root}/src/app.py"},
                      "cwd": root, "session_id": "bench"})
times = []
for _ in range(20):
    start = time.perf_counter()
    subprocess.run([sys.executable, "pre_tool_use.py"], input=payload, capture_output=True, text=True)
    times.append((time.perf_counter() - start) * 1000)
print(f"{statistics.median(times):.1f}")
PY
)
if awk "BEGIN{exit !($PRE_MEDIAN < 150)}"; then pass "median ${PRE_MEDIAN}ms < 150ms"; else fail "median ${PRE_MEDIAN}ms exceeds 150ms"; fi

section "Isolation: hooks never write into a project's .claude directory"
# Only quoted path literals count; prose mentions of ~/.claude in docstrings are not paths.
OFFENDERS=$(grep -rnE '"[^"]*\.claude[^"]*"' "$HOOKS"/*.py "$HOOKS"/lib/*.py \
            | grep -v 'Path.home()' | grep -v '"~/' || true)
if [ -n "$OFFENDERS" ]; then
  printf '%s\n' "$OFFENDERS"
  fail "a hook builds a .claude path not anchored to \$HOME"
else
  pass "all .claude path literals are \$HOME-anchored"
fi

section "Configuration"
SETTINGS="$HOME/.claude/settings.json"
if jq -e '.hooks' "$SETTINGS" >/dev/null 2>&1; then pass "settings.json has a hooks key"; else fail "settings.json missing hooks key"; fi
if jq -e '.enabledPlugins["superpowers@claude-plugins-official"]' "$SETTINGS" >/dev/null 2>&1; then
  pass "pre-existing settings keys preserved"
else
  fail "pre-existing settings keys were lost"
fi
if ls "$HOME"/.claude/settings.json.bak-* >/dev/null 2>&1; then pass "backup present"; else fail "no settings backup"; fi
if grep -qE '"type"[[:space:]]*:[[:space:]]*"(agent|prompt)"' "$SETTINGS"; then
  fail "an LLM-backed hook is wired on a hot path"
else
  pass "no LLM calls on hot paths"
fi
MATCHER=$(jq -r '.hooks.PreToolUse[0].matcher' "$SETTINGS" 2>/dev/null)
MISSING=""
for tool in Bash Read Edit Write; do
  case "$MATCHER" in *"$tool"*) ;; *) MISSING="$MISSING $tool";; esac
done
if [ -z "$MISSING" ]; then pass "PreToolUse matcher covers Bash/Read/Edit/Write"; else fail "PreToolUse matcher missing:$MISSING"; fi
if grep -qi 'not a security boundary' "$HOME/.claude/hooks/README.md"; then
  pass ".agentignore limitation documented"
else
  fail "README does not state the .agentignore limitation"
fi
if [ "$(ls "$HOME"/.claude/skills/gentic*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')" = "6" ]; then
  pass "6 gentic skills globally available"
else
  fail "expected 6 global gentic skills"
fi

section "Result"
if [ $FAILURES -eq 0 ]; then
  printf '  \033[32mall checks passed\033[0m\n'
else
  printf '  \033[31m%d check(s) failed\033[0m\n' "$FAILURES"
fi
exit $((FAILURES > 0))
