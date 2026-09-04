# Decisions: gentic-evals

Interview held under the user's blanket delegation ("I fully trust your decisions here"; "go
ahead"). The brain was asked first: `preference` knows nothing yet about these topics.

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Eval engine | **A home-grown runner, `evals/run.py`, over `claude -p`**, reading the official case layout unchanged. | Wait for `claude plugin eval`; write cases in a private format | The official command is early-access and disabled here; the layout is documented and cheap to honour, so the switch later is a one-line change. | user — delegated |
| Ablation arms | `with` = the user's installed setup; `without` = `--setting-sources project`. | `--bare`; a scratch `CLAUDE_CONFIG_DIR` | Verified: the project-only arm drops every user skill and hook and keeps OAuth; `--bare` needs an API key; a scratch config dir loses login. | user — delegated |
| Graders | `regex`, `file_exists`, `tool_used` only; `llm` and `baseline` unsupported and rejected with a clear message. | Support `llm` via a judge call | A judge that is itself an LLM is the thing under test; deterministic graders make the score reproducible and free. | user — delegated |
| Model | `sonnet` default, `--model` overrides. | The user's default model (fable); haiku | The workflow is what is measured; sonnet is cheaper than fable and far better at following skills than haiku. Flagged: the with/without delta may differ by model. | user — delegated |
| Cost bounds | Per run `--max-budget-usd 3`, suite ceiling 21 USD, `runs: 1` default, never inside `run.sh`. | No caps; official defaults (3 runs) | Fibonacci; real money is spent only on purpose. | user — delegated |
| Where scores go | New brain table `evals` + `brain evals` (per case: with/without pass rate, delta, cost, latest suite id); each suite run is a brain `run` with stamps. | JSON files only under `evals/results/` | The brain is the self-improvement substrate; JSON results are still written for humans. R1's "exact subcommand set" is extended by one. | user — delegated |
| Agent fixtures | Eval cases that dispatch the agent by name in the with arm. | A separate `claude -p` harness per agent | One mechanism, one cost model, and the without arm shows what a session lacks without the agent. | user — delegated |
| Manifest | `.claude-plugin/plugin.json` (name `gentic`, version, description, `experimental.evals: "evals"`). | None until the command is enabled | Costs one file; makes `claude plugin eval .` work the day it turns on. `install.sh` ignores it. | user — delegated |
| Live proof | One real `--arm both --runs 1` suite run at Iterate, results pasted and kept in the brain. | Offline tests only | A fitness function that has never produced a number is not one. Cost accepted under the ceiling. | user — delegated |
