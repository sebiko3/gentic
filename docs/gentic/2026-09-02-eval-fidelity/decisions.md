# Decisions: eval-fidelity

Under the user's blanket delegation; the turn budget was delegated explicitly ("you decide on
the turn budget").

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Turn budget for workflow cases | **55** (`max_turns: 55` on `csv-export-probe`), per-run cap **3 USD**. | 34; 89; unlimited with cost cap only | R2 measured 22 turns for Scout and Interview alone. Masterprompt (write, critic dispatch), Execute (2–3 test-first tasks), Iterate (auditor, report) need the rest; 55 is the next Fibonacci number above the estimate and 22 turns cost 0.55 USD, so 55 fits under 3 USD. 89 would let a stuck run burn the cap. | user — delegated |
| Exhausted runs | **Graded**: `subtype error_max_turns` marks `exhausted`, not `is_error`; graders see created files, tool uses, and the last assistant text block as the last message. | Keep scoring 0 | An exhausted run produced real artefacts; zeroing them hid R2's brief. A genuine error (non-zero exit without `error_max_turns`, scaffold failure, timeout) still scores 0. | user — delegated |
| Transcripts | Every run's stdout to `transcript.jsonl` and stderr to `stderr.txt` in its workspace; `result.json` names them. | None (status quo) | R2 could not say what the executor replied. | user — delegated |
| Agent graders | Assert output shapes the definitions promise; `used-the-agent` matches `"subagent_type": "<name>"`. | Keep vocabulary graders | R2 lesson #5: a built-in agent passes vocabulary graders. | user — delegated |
| Runs per case | Agent cases `runs: 3`; workflow case `runs: 1`. | 1 everywhere; 3 everywhere | Agent replies vary run to run; the workflow case costs ten times more and its failure modes are structural. | user — delegated |
| `eval_runs.exhausted` | Add the column with a guarded `ALTER TABLE` in `ensure_schema`. | Encode in `is_error`; a new table | One honest column; the guard makes it idempotent and safe for existing brains. R1's "no migrations" non-goal was that run's scope. | user — delegated |
| Comparison | The live proof prints both suites (`20260902-125057` and the new one) side by side via `brain evals --suite`; no automatic diff feature. | A `brain evals --compare` flag | Non-goal from R2 (no run-over-run diff) still holds; two invocations suffice. | user — delegated |
