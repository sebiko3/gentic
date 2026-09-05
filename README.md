# gentic

A spec-first, test-first, resumable deep workflow for [Claude Code](https://claude.com/claude-code). One command turns a vague request into verified work: informed clarifying questions → a masterprompt that could brief a stranger → execution in small test-first steps → iteration on an escalation ladder whose budget escalates rather than halts.

## Why

We probed a capable agent with a deliberately ambiguous request — *"Add CSV export to the admin dashboard. Should work for the users table and be fast."* — and asked it to narrate its honest default behavior. It reported that it would:

- ask **zero** questions before writing code, silently deciding on its own authority which PII columns to export;
- write **no plan to disk** — "the plan exists in my head" — so a context loss loses everything;
- accept "fast" **by construction, not measurement** — shipping unverified performance claims.

None of that is a capability problem. It is a workflow problem: missing context, missing persistence, missing verification. gentic supplies the workflow.

## The workflow

```mermaid
flowchart LR
    A[Scout\nbrief.md] --> B[Interview\ndecisions.md]
    B --> C[Masterprompt\nmasterprompt.md]
    C --> D[Execute\ntask table]
    D --> E[Iterate\nverify + ladder]
    E -->|rung 5| C
    E -->|rung 8| B
    E -->|all DoD green| F([Done, with evidence])
```

| Phase | Question it answers | Artifact |
|-------|--------------------|----------|
| **Scout** | What does reality already decide? | `brief.md` — facts, patterns, open decisions each with a recommended default |
| **Interview** | What must the user decide? | `decisions.md` — only high-leverage × high-uncertainty questions get asked (≤4 per round); data/security calls auto-rank first |
| **Masterprompt** | Could a stranger deliver this? | `masterprompt.md` — mission, decisions, non-goals, and a Definition of Done where every item names its exact check **and its test contract**. Then a six-scan critique pass. |
| **Execute** | What's the smallest verified step? | task table in `progress.md` — fibonacci-sized tasks, dependency-ordered riskiest-first, run through [`gentic-tdd`](.claude/skills/gentic-tdd/SKILL.md), one commit per task, each row carrying the failure that was actually observed |
| **Iterate** | Patch, rework, or re-open the spec? | iteration log in `progress.md` — evidence for every DoD item; failures climb a ladder instead of looping |

Every artifact lives in `docs/gentic/<date>-<slug>/` and is committed, so **any session — including one that lost its context — resumes any run** by reading the run directory.

## The test-first spine

Spec-driven and test-driven are one mechanism here, not two practices bolted together.

**The spec designs the tests.** Every Definition of Done item carries a *test contract* — the test
file, the test name, the behaviour asserted, and **the failure to expect**:

```markdown
- [ ] Empty exports are rejected rather than written
      verify: `pytest tests/test_export.py -k empty`
      contract: tests/test_export.py · test_empty_selection_is_rejected ·
                exporting zero rows raises ExportError · expected RED: `Failed: DID NOT RAISE`
```

Predicting the failure is the load-bearing part: it is how the executing agent knows a RED was the
*right* RED and not a typo. An item with a verify command but no contract is checking work nobody
designed — the critique pass now scans for exactly that.

**The tests gate the work.** [`gentic-tdd`](.claude/skills/gentic-tdd/SKILL.md) owns every task —
no production code without a failing test first, and the real failure text is pasted into the task
row:

| # | Task | Size | Test | RED | Status |
|---|------|------|------|-----|--------|
| 1 | Reject empty exports | 2 | `test_empty_selection_is_rejected` | `Failed: DID NOT RAISE` | done |

**A task with an empty `RED` cell is not done.** The cell is the only place a resumed session can
learn the test was ever seen to fail — memory is precisely what a compaction takes away. Docs and
prompts count as behaviour and get contract tests; `n/a` is reserved for tasks that change nothing
observable, and must say why.

**The hooks record, they never block.** Every recognised verification run — failing or passing —
lands in the brain as a `red` or `verification` event tagged with the run it belongs to, so a
run's RED/GREEN history is one query. No hook ends a turn: the Iterate phase and `dod-auditor`
are the only judges of done-ness.

## The fibonacci mechanics

- **Task sizes** are 1/2/3/5/8 points; a task above 8 must be split (if it can't be, the spec is under-specified).
- **Escalation rungs** cost 1 (micro-fix), 2 (rework component), 3 (redesign within spec), 5 (re-open masterprompt), 8 (re-open interview). Same item fails twice at a rung → the next rung is mandatory. No third tries.
- **The budget is 13 points per run.** When it's gone, the ladder escalates instead of halting: the next failure re-opens the spec (rung 5), a second exhaustion re-opens the Interview (rung 8), which resets the budget. A run never stops itself; only the `STOP` file ends one early.

The costs grow super-linearly because each rung discards more prior work — and the budget forces a real decision between many small fixes and one deep rethink.

## The agents

Five subagents, each closing a gap the workflow had left to improvisation. All five are plain
markdown in [.claude/agents/](.claude/agents). None of the reviewing three is given an edit
tool. `masterprompt-critic` is fully read-only (`Read, Grep, Glob`); `code-reviewer` and
`dod-auditor` also get `Bash`, which they need to run `git diff` and to execute the checks a
Definition of Done names — so for those two the guarantee is narrower than "cannot": no direct
file-editing tool, plus an instruction not to edit. `.claude/hooks/tests/test_structure.py`
pins each agent's declared tools so this claim and the frontmatter cannot drift apart.

| Agent | Fires when | What makes it useful |
|-------|-----------|----------------------|
| [`code-reviewer`](.claude/agents/code-reviewer.md) | `/review` or `/ship` | Correctness, security, and silent failures — scored 0-100 and **reported only at ≥80**. A reviewer that reports everything gets skimmed and then ignored. |
| [`dod-auditor`](.claude/agents/dod-auditor.md) | the Iterate phase, before any completion claim | Runs each Definition-of-Done check literally and returns PROVEN / FAILED / **UNVERIFIABLE**. It may never edit a DoD item to make it pass, and never rounds unverifiable up to proven. |
| [`masterprompt-critic`](.claude/agents/masterprompt-critic.md) | the Masterprompt critique pass | Gets the spec and nothing else — no brief, no decisions, no conversation. That withheld context is the instrument: it occupies the position of the agent who executes this after a compaction. |
| [`task-executor`](.claude/agents/task-executor.md) | Execute fan-out, on independent 3+ point tasks | Does one task test-first and returns a fixed evidence block. Refuses a vague assignment instead of guessing — it has no channel back to the user, so improvising is how a fan-out produces four readings of one spec. |
| [`ui-tester`](.claude/agents/ui-tester.md) | a `ui` Definition-of-Done item, a UI failure to reproduce, or a product to inspect before changing it | Drives the real browser (Claude in Chrome first, the in-app Browser as fallback), files a half-scale screenshot under the run's `evidence/` directory, and reports what the screen showed — literally. It is given the page and the flow, never the spec. |

`ui-tester` is the one agent whose tools are not pinned: it must inherit the browser tools, so
its own text is what forbids it to edit.

Review runs when you ask for it: `/review` on its own, or `/ship`, which reviews before it
commits. Nothing nags and nothing blocks — the hooks only record.

## The brain

gentic remembers. One SQLite file, `~/.claude/gentic/brain.sqlite` (set `GENTIC_BRAIN` to put it
elsewhere), holds what earlier runs learned, what the user has decided, and what the hooks saw —
across every project on the machine, keyed by repository name. It is the agent's own memory, and
it may use it as it likes:

```bash
python3 ~/.claude/hooks/lib/brain.py note calendar-dnd "drag and drop needs pointer events on touch"
python3 ~/.claude/hooks/lib/brain.py recall pointer events
python3 ~/.claude/hooks/lib/brain.py preference artifact-location     # exit 1 until learned
python3 ~/.claude/hooks/lib/brain.py lessons
python3 ~/.claude/hooks/lib/brain.py sql "select kind, count(*) from events group by kind"
```

| What it holds | Who writes it | Who reads it |
|---------------|---------------|--------------|
| `events` — every `red` and `verification` run, tagged with the open run | the hooks, automatically, best-effort | you, via `sql`; later runs' tooling |
| `sessions` — the concurrency valve's per-session counter | the hooks, automatically, best-effort | the valve itself |
| `decisions` and learned preferences | the Interview (`--source user`), the Masterprompt (`--source default`) | the Interview, before it asks |
| `lessons` — what each spent rung taught, and *who caught it* | the Iterate phase | the Scout phase, before it explores |
| `notes` with full-text recall | the agent, whenever something is worth keeping | the Scout phase; anyone |
| `runs` and `stamps` — lifecycle and the sha256 of every skill a run used | the `gentic` skill | future evals, to tie a lesson to a skill version |

The rules are the ones the rest of the setup already lives by. **A brain that is missing, locked
or unwritable is invisible**: the hooks give up within a 34 ms lock timeout and print nothing,
and the harness measures the writing hook against the same 150 ms budget as the others.
**The user's memory is never a test fixture**: `run.sh` and every test point `GENTIC_BRAIN` at a
throwaway file. **A preference is learned, not assumed**: the Interview adopts an answer only
after the user has given it twice, the most recent user answer wins, and defaults never teach.

`sql` is deliberately unrestricted — the agent may create its own tables. Before any `DROP`,
`DELETE`, `UPDATE` or `ALTER` the file is copied to `brain.sqlite.bak`, one level of undo.
Commands recorded as events have credentials scrubbed (`Authorization:`, `--password`,
`token=`, `AWS_…=`); notes are not scrubbed, so never note a secret. The schema is versioned
(`PRAGMA user_version`): an older brain is upgraded in place on first open by additive, guarded
migrations, and rows are never rewritten. Two tables grow on their own and are bounded:
`prune` deletes `events` older than 89 days and `sessions` idle for 8, and every session start
prunes quietly. The hooks keep no JSON state anywhere — the `sessions` table is the whole of
it. SQLite's write-ahead log assumes a local disk — a home directory synced by iCloud or
Dropbox is a known hazard; keep the brain out of synced folders.

The [`gentic-brain`](.claude/skills/gentic-brain/SKILL.md) skill carries the full command set
and says where each phase uses it.

## The fitness function

gentic can be scored. `evals/` holds five cases in the case layout that `claude plugin eval`
documents for Claude Code 2.1.258 — `prompt.md` with frontmatter, `graders/*.md`, an optional
`case.yaml` with a scaffold script — and `evals/run.py` runs them, because the official command
is still early-access and disabled on ordinary accounts (the layout is honoured, the command
itself is unverified here):

```bash
python3 evals/run.py --dry-run          # preflight, list cases and the exact claude argv, spend nothing
python3 evals/run.py                    # both arms, one run per case, sonnet, budgets 5 / 21 USD
python3 ~/.claude/hooks/lib/brain.py evals   # `brain evals`: the latest suite's numbers, from the brain
```

Every case runs twice, headlessly through `claude -p` in a fresh workspace: the **with** arm
sees your installed setup exactly as you do; the **without** arm passes
`--setting-sources project`, which loads no user skills, hooks or agents. The difference is
the score. Graders are deterministic — `regex` over the final message or the created files,
`file_exists` over files the agent created, `tool_used` over the transcript — so a number is
reproducible and free to compute; only the sessions cost money, and they are capped at 5 USD
per run and 21 USD per suite, checked before each launch. Nothing runs the suite unattended,
and the hook harness never invokes it.

| Case | What it measures |
|------|------------------|
| `csv-export-probe` | The README's own probe: a vague request against a small admin dashboard. Did a brief get written before code, and was exporting `password_hash` surfaced as a decision? |
| `dod-auditor-false-claim` | A masterprompt claims two files exist; one does not. Does the auditor say FAILED? |
| `critic-finds-contradiction` | Constraints forbid the network; a DoD item requires a download. Does the critic name that collision? |
| `executor-refuses-vague` | "improve the code", no spec. Does the executor refuse instead of guessing? |
| `reviewer-seeded-defect` | The seeded-defect fixture. Both planted defects found, the naming decoy not reported? |

Scores land in two brain tables, `eval_runs` and `eval_graders`, next to the sha256 stamps of
the installed skills and agents that produced them — so a change to a skill can be compared
before and after. A `with` case below 1.0 is a finding about the workflow and becomes a brain
`lesson`; the case is never loosened to pass. Results also go to `evals/results/<suite>/`
(git-ignored) for humans: every run's raw `transcript.jsonl` and `stderr.txt` under `runs/`.
Workspaces themselves live under the system temp directory, never inside this repository — a
workspace inside the checkout would inherit its project root, and with it this repo's agents
and skills, handing the "without" arm the very things it must lack.

Three fidelity rules, each learned from the first live suite. A session that runs out of turns
is **exhausted**, not failed: the CLI reports `error_max_turns` with no final message, so the
runner grades what the session created and did and takes its last spoken text as the last
message; the console and `brain evals` mark such an arm `exhausted`. The workflow case gets
**89 turns** and every run a **5 USD** cap: gentic's Scout and Interview alone took 22 turns in
the first suite, a 21-turn limit scored a written brief as nothing, and 55 turns finished a
three-task feature twice with no headroom and then cut a third run off mid-Execute. Agent cases
run three times (`runs: 3` in their frontmatter) because a single reply is noise, and their
graders assert the shape each agent definition promises — the auditor's `UNVERIFIABLE` verdict
and closing count, the critic's five named scans, the executor's `status:` line, the reviewer's
`confidence <n>` and `Not reported` — rather than vocabulary a built-in agent also produces.

## UI contracts

A behaviour a person sees or clicks is a Definition-of-Done item like any other, with a
contract that names its test:

```markdown
- [ ] Dragging an event to another day moves it
      verify: `npx playwright test tests/e2e/calendar.spec.ts`
      contract: ui · tests/e2e/calendar.spec.ts · test_drag_event_to_new_day ·
                the event renders under the target day · expected RED: `locator not found`
```

The executable half is always the project's own e2e runner — Playwright, Cypress, whatever it
already runs; the hooks count those runs as verification evidence. The browser is for evidence
and exploration, not for the test: the `ui-tester` agent opens the flow in Claude in Chrome
(fallback: the in-app Browser), files a half-scale screenshot under
`docs/gentic/<run>/evidence/`, and reports what it saw. A project with no e2e runner gets a
`ui-tester` verification instead, and the item is flagged `not reproducible in CI` so nobody
mistakes the screenshot for a test. When the request touches a user-facing surface, Scout
starts the app first, walks its routes, and puts a feature inventory with screenshots into the
brief — questions asked from a screenshot are sharper than questions asked from `ls`. Never
screenshot a production or authenticated surface or real personal data; fixture and seed data
only.

## The release lane

`/ship` can continue past the pull request, but only as far as the project's grants allow, and
every step past "watch" is a script's answer rather than an agent's memory:

```bash
python3 ~/.claude/hooks/lib/release.py checks --pr 12        # exit 0 green · 1 red · 2 pending · 3 no checks · 6 gh failed
python3 ~/.claude/hooks/lib/release.py wait --pr 12          # polls every 21 s, up to 1597 s; exit 4 on timeout
python3 ~/.claude/hooks/lib/release.py failed-logs --pr 12   # the failing jobs' last 89 lines
python3 ~/.claude/hooks/lib/release.py merge --pr 12         # refuses unless granted, own repo, open, green
```

Red checks feed back as at most two rung-1 fixes per ship, each test-first with its own commit;
a third failure stops with the logs in the report. `merge` is gated four ways — `merge-on-green`
granted and the project trusted, the target repository is the checkout's own, the PR open and
not conflicting, every check green — and is the one exception to `/ship`'s never-merge rule.
`--through preview` deploys with the project's own mechanism and hands the URL to `ui-tester`;
without a grant each step reports what it would have done. This repository's own CI is the
offline hook harness on GitHub Actions (`.github/workflows/gentic.yml`), never the eval suite.

## Standing authorizations

A run never pushes and never opens a PR unless you have said so — once, durably, and in two
places, because a clone must never be able to grant itself. In the project's root `CLAUDE.md`:

```markdown
## gentic authorizations
- push
- open-pr — CI is required on this repo, so a PR is safe to open
```

and on the machine, one git-root path per line in `~/.claude/gentic/trusted-projects`, a file
only you write. The helper answers from both, and fails closed on anything missing:

```bash
python3 ~/.claude/hooks/lib/project_conventions.py authorized push      # yes / no, exit 0 / 1
python3 ~/.claude/hooks/lib/project_conventions.py authorized --list    # granted and trusted words
```

Today only `push` and `open-pr` are consumed: a run whose project grants both ends its Iterate
phase by following `/ship`'s own steps and reporting the PR URL. `merge-on-green`,
`deploy-preview`, `use-workflow-tool` and `spawn-teams` are reserved words for the release lane
and the orchestrator mesh. To halt a run from outside, create `docs/gentic/<run>/STOP` (or say
`/gentic stop <slug>`): the next task or rung writes a handoff and ends; delete the file to
resume. That is the only early end — an autonomous run never stops itself, takes rung 5 and
rung 8 on its own, and escalates instead of halting when its budget is spent. A hook also
refuses a sixth concurrent foreground subagent per session.

## Install

```bash
./install.sh
```

That copies this repo's `.claude/` — skills, agents, hooks, commands — into `~/.claude/`, so
the setup applies to every project, not just this one. It is idempotent, and it only ever
writes the files this repo ships: your own skills, agents, sessions, and plugins are never
touched, and there is no `rm -rf` or `--delete` anywhere in it.

```bash
./install.sh --check
```

Reports any file that has drifted from the repo and exits non-zero, changing nothing.

Hooks and skills take effect immediately. **Agents are resolved when a session starts**, so a
newly installed agent is not invocable in the session that installed it — start a new one.

For gentic alone, without the hooks and agents, copy `.claude/skills/gentic*` into your repo's
skills directory and add the **Routing** section from [CLAUDE.md](CLAUDE.md) to your own — the
workflow is markdown with no dependencies.

Works standalone — the test-first discipline is gentic's own skill, not a borrowed one. If the [superpowers](https://github.com/obra/superpowers) plugin is installed, gentic composes with it (TDD, systematic debugging, verification before completion) at marked points.

## Adopting gentic in a project

gentic names its own branches `gentic/<slug>` and its own commits `gentic(<slug>): …` — but
only in projects that asked for it. Everywhere else it follows the conventions already in the
repository, because a workflow that renames your branches is a workflow you uninstall.

A project counts as **adopted** when its root `CLAUDE.md` contains the literal string
`gentic/<slug>` — which it does automatically if you copied the **Routing** and **Conventions**
sections from [CLAUDE.md](CLAUDE.md) as the install instructions describe.

In any other project the branch prefix is read from the branches already there:

| the project's branches | gentic uses |
|---|---|
| `feat/…` ×3, `fix/…` ×2 | `feat/<slug>`, and plain commit subjects |
| `main`, `websockets` | `<slug>`, and plain commit subjects |
| a tie, or a prefix seen once | `<slug>` — inventing a convention is the bug being avoided |

Ask it directly at any time:

```bash
python3 ~/.claude/hooks/lib/project_conventions.py branch my-slug
```

The helper only *prints* a name; it never creates a branch, never writes to a `CLAUDE.md`, and
never fails a run — if anything goes wrong it falls back to the bare slug.

## Verifying the setup

```bash
bash .claude/hooks/tests/run.sh
```

Exit 0 with no `FAIL` lines means the hooks behave, the installer is safe, and the setup is
structurally sound — every agent's frontmatter parses, and every skill, command, agent, and
hook that anything references actually exists. That last check is not hypothetical: this repo
shipped a `/ship` command that invoked three agents from a plugin whose recorded install
directory did not exist. Nothing errored; review just quietly fell back to less than it
claimed. `test_structure.py` exists so that class of defect cannot pass unnoticed again.

## Use

```
/gentic add rate limiting to the public API
```

- New non-trivial task → gentic starts a run and interviews you (up to 4 multiple-choice questions per round, recommendation listed first).
- You're away, or the session is headless (`claude -p`, no `AskUserQuestion`)? Runs don't block and don't stop to flag: gentic adopts the scouted default for each question, flags it `unconfirmed`, continues through every phase, and lists every assumption in the final report.
- `resume` / `continue` → gentic finds the newest unfinished run and re-enters at the first unchecked phase.
- `/gentic status` → every run, its phase, tasks done, budget remaining.

## Example run

This repository built itself with its own workflow — see [docs/gentic/2026-08-11-bootstrap-gentic/](docs/gentic/2026-08-11-bootstrap-gentic/) for a complete run: the brief, the decisions (with alternatives considered), the masterprompt with its Definition of Done, the brief including the baseline probe quoted above, and an iteration log of real fixes from the run's own review gates.

## Design notes

- **Why five phases instead of "questions → masterprompt → iterate"?** The original three-phase shape lacks grounding (questions asked from ignorance are generic) and an anchor for iteration (without a checkable Definition of Done, iteration spins). Scout makes questions sharp; the DoD makes iteration converge.
- **Why not multi-agent-first?** Subagent fan-out is an execution optimization, not a workflow. gentic stays single-threaded by default (cheap, debuggable, no opt-in friction). The four agents are optional accelerants at named points, and each earns its place by being *worse informed* than the main thread in a useful way: `masterprompt-critic` is denied the conversation, `dod-auditor` is denied the author's confidence, `task-executor` is denied the neighbouring tasks. An agent that merely knows what you already know adds cost, not signal.
- **Why do the hooks never block?** A gate that ends a turn is a stop condition, and a stop condition in an autonomous run is a place where the work waits for nobody. The hooks record — every verification run, tagged with its run, into the brain — and the Iterate phase with `dod-auditor` judges; a run ends when its Definition of Done is proven or when the user drops a `STOP` file, never because a hook decided so.
- **Why files instead of memory?** Context windows end; `docs/gentic/` doesn't. The masterprompt's quality bar — "a stranger could deliver from this file alone" — is also exactly what a post-compaction session needs.

## License

[MIT](LICENSE)
