# Brief: self-improving-gentic

## Mission (as understood)

The user wants gentic to grow from a disciplined single-threaded workflow into a system that
takes one short, vague prompt — *"make this calendar app 100% more awesome with all the
knowledge you got"* — and runs the whole delivery stack unattended: scout the product, decompose
the wish into a backlog, spec and build each item test-first, drive automated UI tests, review,
open PRs, wait on CI, deploy previews, and report with evidence. Agents should be spawned on
demand, coordinated by several orchestrators that talk to each other. And the system should
**improve its own loop engineering**: measure how well its skills, hooks and agents perform,
learn from every run, and propose changes to itself that are proven not to regress.

Two constraints frame everything: gentic's existing credibility rests on scarcity (one hard block,
evidence before claims, no unasked git side effects), and the user has already built and shelved
one multi-agent system (`sheldon`). The proposal must add autonomy without eroding the first and
without repeating the second.

## Facts

**What gentic is today**
- 7 markdown skills (`gentic`, `-scout`, `-interview`, `-masterprompt`, `-execute`, `-iterate`,
  `-tdd`), 5 stdlib-only Python hooks, 4 agents, 2 commands, an installer, 220 tests in 12
  suites — ~8.3k lines total (`git ls-files | wc`, `tests/run.sh`).
- The workflow is single-threaded by design; subagent fan-out is an "execution optimization"
  inside Execute only (`README.md` Design notes; `gentic-execute/SKILL.md` "Optional parallelism").
- A `Workflow`-tool orchestration script was considered and rejected on 2026-08-19 as a
  `default — unconfirmed` for portability reasons
  (`docs/gentic/2026-08-19-agent-automation-suite/decisions.md`, "Orchestration approach").
- CI has been an explicit non-goal in every run: bootstrap (`masterprompt.md:22`),
  universal-claude-setup (`:58`), agent-automation-suite (`:113`). An eval harness was a
  bootstrap non-goal too (`:22`).
- Hook state is one JSON file per session under `~/.claude/state/`, pruned after 7 days
  (`lib/common.py` `prune_state`). Nothing survives across sessions except the run artifacts.
  No mechanism reads a finished run's iteration log back into a later run.
- Every run's `progress.md` already contains the raw material of a learning loop: which DoD
  items failed, which rung fixed them, and *what caught the defect* — e.g. "found in live use,
  not by the suite" (agentignore-guard log #2), "9 of 11 points spent on defects the /ship review
  found" (agent-automation-suite header), "Claude Code 2.1.193 does not send prompt_id" found
  only in a live session (universal-claude-setup notes). These lessons are prose, unindexed, and
  never re-read.
- The verification-evidence regex recognises pytest/jest/vitest/go/cargo/etc. but **not
  Playwright, Cypress, Lighthouse or axe** (`post_tool_use.py` `VERIFICATION`; grep confirmed
  empty). A UI test run therefore never counts as evidence for the Stop gate, and no skill or
  agent mentions UI testing at all.
- `code-reviewer` has one seeded-defect fixture (`tests/fixtures/seeded_defect.py`); the other
  three agents have no behavioural test of their own.
- `/ship` ends at "PR opened" by rule (`commands/ship.md` §7 "Never merge"). Nothing watches
  CI, reads its failures, or deploys.
- The `UserPromptSubmit` classifier is deterministic and treats a short imperative prompt as
  trivial unless two signals fire (`user_prompt_submit.py` `detect`): "make this calendar app
  100% more awesome" matches `make` + `better`-class adjectives only if the regex sees them —
  "awesome" is not in the vague-adjective list.

**What the platform offers now (Claude Code 2.1.258, verified in this session)**
- `Workflow` tool: deterministic scripts with `agent()`, `parallel()`, `pipeline()`, phases,
  resume from a prior run id. Opt-in only (user must ask for a workflow).
- Agent teams: `ListAgents` / `SendMessage` to continue or message long-lived subagents, local
  sessions and cloud sessions.
- Scheduling: `CronCreate`, `ScheduleWakeup` (self-paced loops), cloud "routines" via the
  `schedule` skill, `RemoteTrigger`.
- `Monitor` for waiting on external state (CI runs) without polling loops.
- Browser MCP (`preview_start`, `navigate`, `read_page`, `find`, screenshots), Claude in Chrome,
  iOS Simulator control — UI can be driven and screenshotted from a session.
- GitHub MCP (PRs, reviews, merges, Copilot review), Railway MCP (deploy, logs, metrics).
- `claude plugin eval` with `--ablation with-without`, LLM graders (`graders/*.md`), cost
  ceilings, JSON results — a first-party fitness function for skills (`claude plugin eval --help`).
- `/skill-doctor` and `claude plugin details` (component inventory + token cost).

**Prior art the user owns**
- `sheldon` (marketplace `sebiko3/sheldon`, disabled): Orchestrator (opus) → Worker (sonnet) →
  Validator (haiku); numbered executable assertions in `contract.md`; `mission/<id>` branch per
  feature; a "persistent learning brain" (`mcp/missions-server/src/brain.ts`); an
  `epic-planner` agent. Its contracts are gentic's DoD test contracts under another name; its
  brain is the learning loop gentic lacks; its epic-planner is the decomposition step a short
  prompt needs.
- `ruflo` swarm / autopilot / federation plugins are registered and disabled — the user has
  looked at swarm-style orchestration and not adopted it.
- `zcontext` global skill: a SQLite context store for per-task facts and preferences.

## Patterns to follow
- Deterministic-first: anything that must hold under context pressure is a script or a hook,
  not prose (`project_conventions.py` docstring; decisions.md "Mechanism" row).
- Every agent earns its place by being *worse informed* than the main thread in a useful way
  (`README.md` Design notes). New orchestrators must pass the same test.
- Docs and prompts are behaviour and get contract tests (`tests/test_structure.py`).
- Advisory nudges, once per session; exactly one hard block (`stop.py` docstring).
- Fibonacci for every balancing number (task sizes, rungs, budget 13, `CAT_LIMIT` 89k, `REPORT_AT` 55k).
- Repo is canonical, `install.sh` syncs to `~/.claude`, `--check` detects drift.

## Constraints discovered
- `~/.claude/CLAUDE.md`: no commits/pushes/PRs/deploys unless asked. Autonomy therefore needs an
  explicit, durable authorization mechanism — it cannot be assumed.
- ROUTING.md: never push, never open a PR inside a run; `/ship` is the only git automation and
  only the user types it. Any "release lane" must extend `/ship` or be a new explicitly typed
  command, not a silent phase.
- Hooks: stdlib only, no subprocess, no network, 150 ms median budget on hot paths.
- Portability claim: gentic "is markdown with no dependencies". Platform features (Workflow,
  teams, cron, MCPs) must be *adapters with a prose fallback*, detected at run start.
- The `Workflow` tool may only run when the user opts in (tool contract) — an orchestrator that
  wants it must ask once and record the answer as a standing authorization.

## Improvement catalogue

Eighteen mechanisms, grouped by what they buy. Each names the gap it closes (from Facts), the
platform feature it rides on, and its Fibonacci cost as a run.

### A. The flywheel — how gentic improves itself

1. **Evals as the fitness function.** Package gentic as a plugin with an `evals/` directory:
   cases like the bootstrap probe (*"Add CSV export… should be fast"*) graded on: asked ≤4
   questions, wrote `brief.md`, every DoD item names a test contract, no code before Execute.
   `claude plugin eval --ablation with-without` gives a with/without score delta per case —
   the number that today exists only as folklore in the README's "Why". No skill or hook change
   may lower it. *Gap:* no eval harness since bootstrap. *Cost:* 5.
2. **Agent fixture bank.** Generalise the one seeded-defect fixture: `dod-auditor` must mark a
   planted false claim FAILED; `masterprompt-critic` must find a planted contradiction;
   `task-executor` must return `assignment unclear` on a vague brief. Run under `claude -p`
   from `run.sh`. Unit tests for agents. *Cost:* 3.
3. **Lesson ledger.** Iterate's final report additionally writes `retro.md` plus one JSON line
   per DoD failure to a machine-wide `~/.claude/gentic/lessons.jsonl`: item, rung, root cause
   class, *what caught it* (suite / live / review / user), skill versions in force, points and
   tokens spent. Machine-readable so a later agent can cluster it. *Gap:* lessons never
   re-read. *Cost:* 3.
4. **Skill-version stamping.** `progress.md` records a hash of every skill and agent file the
   run used. Lessons become attributable to a version, so two versions of a skill can be
   compared on real runs, not just evals. *Cost:* 1.
5. **Preference memory for the Interview.** Every `user`-sourced decision and every
   confirmed default is stored (via `zcontext` or a small store) keyed by topic. The Interview
   consults it before asking: a question the user has answered the same way twice is adopted
   silently with Source `learned`. This is how "one short prompt" becomes possible without
   removing the Interview: questions converge to zero per user, not per run. *Cost:* 3.
6. **The gardener.** A scheduled routine (weekly, `CronCreate` or a cloud routine) that reads
   the ledger, clusters recurring failure classes, proposes *one* change to a skill, hook or
   agent, opens a gentic run for it on a branch, runs the evals with ablation, and opens a PR
   only if no score regresses. A human merges. Bounded: one proposal per week, budget 13,
   `--max-cost-usd`. *Gap:* the loop engineering is done by hand today. *Cost:* 8.
7. **Adjective compiler.** A catalogue mapping vague words to measurable proxies, seeded by
   hand and grown from confirmed DoD items: *fast* → p95 latency; *awesome* (UI) → axe
   violations 0, Lighthouse ≥ 89, every interactive state has a test, empty/error/loading
   states exist, keyboard-reachable. The Masterprompt draws from it; the Interview asks only
   when the catalogue has no confirmed proxy for the domain. *Cost:* 3.

### B. The pipeline — one short prompt to a shipped product

8. **`gentic-epic`: decomposition orchestrator.** A phase before Scout for prompts that are
   wishes, not tasks. It scouts the *product* (runs it via `preview_start`, screenshots every
   screen, reads the UI, lists features and gaps), generates a candidate backlog, scores items
   leverage × cost in Fibonacci, picks what fits an epic budget (89 or 144 points), and writes
   `epic.md` with a DAG of runs. Each node becomes an ordinary gentic run. This is the top of
   the orchestrator tree. *Prior art:* sheldon's `epic-planner`. *Cost:* 8.
9. **Orchestrator mesh.** Three long-lived orchestrator roles, each worse informed in a useful
   way: **run orchestrator** (owns one run, sees the masterprompt), **QA orchestrator** (owns
   previews and UI tests, sees only DoD contracts and the diff), **release orchestrator** (owns
   `/ship`, CI and deploy, sees only the PR and the evidence). They talk via `SendMessage`
   using the report block `task-executor` already emits — evidence-typed messages, never
   prose. The blackboard is the run directory plus an append-only `bus.jsonl`; any orchestrator
   can die and be resumed from files, the property gentic already has for one thread. *Cost:* 8.
10. **Engine adapters.** Execute's fan-out gets a `Workflow` script adapter
    (`pipeline(tasks, executor, auditor)` — each task audited the moment it lands) and Iterate's
    verification gets a `parallel(dod_items → dod-auditor)` adapter. Prose contract stays the
    fallback; the adapter is chosen at run start by capability detection and a standing
    authorization. Reverses the 2026-08-19 rejection *without* breaking portability. *Cost:* 5.
11. **UI test contracts.** A new contract type in the DoD grammar:
    `contract: ui · tests/e2e/calendar.spec.ts · drag event to new day · expected RED: locator not found`.
    Playwright is the executable form (CI-runnable, project-owned); the Browser MCP is for
    exploratory scouting and for the `ui-tester` agent to reproduce a failure with a screenshot
    saved under the run directory as evidence. Add `playwright|cypress|lighthouse|axe` to
    `VERIFICATION`. *Gap:* confirmed empty grep. *Cost:* 5.
12. **Release lane.** `/ship` gains a `--through ci|preview|merge` argument gated by standing
    authorizations: after the PR opens, `Monitor` the CI run, read failures via the GitHub MCP,
    feed each as a rung-1 fix inside the run's remaining budget, deploy a preview (Railway MCP)
    when green, hand the preview URL to the QA orchestrator for the UI smoke, and auto-merge
    only when the project's authorization says so. Also generates
    `.github/workflows/gentic.yml` (project verification + hooks harness) on request. *Gap:*
    `/ship` stops at PR; CI a non-goal in every run. *Cost:* 8.
13. **Product scout.** `gentic-scout` gets a "runnable product" variant: if the project has a
    dev server, start it, walk every route with the Browser MCP, and put screenshots and a
    feature inventory in the brief. Questions asked from a screenshot are sharper than
    questions asked from `ls`. *Cost:* 3.

### C. Economics and safety of autonomy

14. **Standing authorizations.** A `## gentic authorizations` section in the project's
    `CLAUDE.md` (where the adoption marker already lives) listing what the user has
    pre-approved: `push`, `open-pr`, `merge-on-green`, `deploy-preview`, `use-workflow-tool`,
    `spawn-teams`. Absent means today's behaviour. `project_conventions.py` grows an
    `authorized <action>` subcommand so skills ask a script, not memory. This is the *only*
    honest way to reconcile "one short prompt does everything" with the no-unasked-side-effects
    rules — the user authorises once, durably, per project. *Cost:* 3.
15. **Budget as a currency across orchestrators.** Epic budget 89/144, run budget 13, rung
    costs unchanged. Orchestrators cannot mint points; a child run exhausting its budget hands
    off upward with the same honest handoff. Token estimates from the existing spend ledger
    become a second currency with a per-epic ceiling. *Cost:* 2.
16. **Concurrency valve and kill switch.** A hook refuses spawning more than 5 concurrent
    agents per session (Fibonacci) and `/gentic stop <run|epic>` writes a stop flag every
    orchestrator checks between tasks. Same valve philosophy as the token guards: deny once,
    never loop. *Cost:* 2.
17. **Cross-project status.** `/gentic status` aggregates every repo's runs, budgets and
    stalled orchestrators, rendered as an artifact dashboard; a "babysitter" `ScheduleWakeup`
    loop checks stalled runs and resumes them. *Cost:* 3.

### D. Meta

18. **Retire sheldon into gentic.** Its brain → lesson ledger + preference memory (3, 5); its
    contracts → DoD test contracts (already); its epic-planner → `gentic-epic` (8); its
    Orchestrator/Worker/Validator triad → run orchestrator / `task-executor` / `dod-auditor`
    (already). Running two systems is how neither improves. *Cost:* 1 (an ADR and an archive note).

### How the calendar prompt would flow (the target behaviour)

```
"make this calendar app 100% more awesome"
  → classifier: wish-shaped prompt → gentic-epic
  → product scout: dev server up, 7 screens screenshotted, feature inventory, a11y scan
  → adjective compiler: "awesome" → 6 measurable proxies (confirmed for UI domain last epic)
  → backlog of 21 candidates, scored; epic budget 89 → 9 runs chosen, DAG written to epic.md
  → interview: 0 questions (preference memory answered all), 2 defaults flagged
  → 9 runs: run orchestrators (3 concurrent, valve 5), each Scout→Iterate with test contracts
      ├ task-executors fan out per run (Workflow adapter, authorized)
      ├ QA orchestrator: Playwright contracts RED→GREEN, screenshots as evidence
      └ dod-auditor per run, adversarial
  → release orchestrator: /ship --through preview per run; CI watched; 2 CI failures fixed
      at rung 1; previews deployed; UI smoke green; PRs opened, merged on green (authorized)
  → final report: 9 PRs, evidence per DoD item, 4 unconfirmed defaults, 11 of 89 points spent
  → lesson ledger: 3 new lines; gardener next Sunday proposes one skill change, evals gate it
```

## Roadmap (each row is its own gentic run; order is dependency, then leverage)

| # | Run slug | Contains | Size | Why this order |
|---|----------|----------|------|----------------|
| R1 | `gentic-evals` | 1, 2, and the `VERIFICATION` regex fix from 11 | 8 | A self-improving system needs a fitness function before anything else changes; also the cheapest proof that gentic works. |
| R2 | `lesson-ledger` | 3, 4, 5, 7 | 8 | Turns every past and future run into training data; makes the Interview converge. |
| R3 | `standing-authorizations` | 14, 15, 16 | 5 | The consent layer everything autonomous depends on; small, deterministic, testable. |
| R4 | `ui-contracts` | 11, 13, `ui-tester` agent | 8 | "Awesome" for an app is mostly UI; without UI evidence the epic cannot be verified. |
| R5 | `release-lane` | 12 | 8 | Closes the loop from PR to CI to preview; the first time a run ends in a deployed URL. |
| R6 | `gentic-epic` | 8 | 8 | The decomposition orchestrator; needs R2's compiler, R3's budget currency, R4's product scout. |
| R7 | `orchestrator-mesh` | 9, 10, 17 | 8 | Concurrency last: cheap course correction is worth more than parallelism until the pieces are proven single-threaded. |
| R8 | `gardener` | 6, 18 | 8 | The self-improvement routine; gated by R1's evals and fed by R2's ledger. |

Total ≈ 61 points across eight runs; each run keeps its own budget of 13.

## Open decisions (ranked by leverage)

1. **Which run starts first** — options: R1 evals / R3 authorizations / R6 epic (the visible
   feature). Recommended default: **R1 `gentic-evals`**, because every later change to skills
   or agents is otherwise unmeasurable, and it is the smallest run with the largest downstream
   effect.
2. **Orchestration engine** — options: A) prose contracts only (status quo); B) `Workflow`
   scripts inside a run, agent teams between orchestrators, both behind capability detection
   with prose fallback; C) a custom MCP server like sheldon's. Recommended default: **B**,
   because it uses first-party machinery, keeps the portability claim via fallback, and avoids
   maintaining a server.
3. **Where standing authorizations live** — options: project `CLAUDE.md` section / a
   `.gentic.toml` / `~/.claude` machine-wide. Recommended default: **project `CLAUDE.md`
   section, none by default**, because the adoption marker already lives there, it is
   reviewable in git, and a machine-wide grant would authorise pushes in repos the user never
   meant.
4. **UI testing executable** — options: Playwright in the project / Browser MCP only /
   both. Recommended default: **Playwright as the DoD contract, Browser MCP for scouting and
   failure reproduction**, because contracts must be reproducible in CI and MCP sessions are not.
5. **CI generation** — options: never touch CI (status quo non-goal) / generate a GitHub
   Actions workflow on request / always. Recommended default: **on request, per project**,
   because CI is another project's public surface and belongs under authorization 3.
6. **Self-improvement cadence** — options: on-demand `/gentic evolve` / scheduled weekly
   routine / continuous after every run. Recommended default: **on-demand first, scheduled
   after two clean on-demand cycles**, because an unattended loop that rewrites its own skills
   must first prove the eval gate catches regressions.
7. **Lesson ledger location** — options: machine-wide `~/.claude/gentic/lessons.jsonl` plus a
   committed per-run `retro.md` / per-repo only. Recommended default: **both**, because
   lessons about the *workflow* are cross-project while lessons about the *product* belong with
   the code.
8. **sheldon's fate** — options: absorb its concepts and archive it / keep both / revive it as
   the orchestrator. Recommended default: **absorb and archive with an ADR**, because its three
   mechanisms map one-to-one onto items 3, 5 and 8, and its MCP server is the maintenance burden
   the deterministic-script style avoids.
