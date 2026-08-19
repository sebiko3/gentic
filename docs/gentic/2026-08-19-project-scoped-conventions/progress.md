# Run: project-scoped-conventions
Goal: gentic follows each project's own branch and commit conventions instead of imposing its own everywhere.
Iteration budget: 13 remaining (0 spent — no DoD item failed verification) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [x] 4 Execute
- [x] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Status (pending/in progress/done) |
|---|------|------|------------|--------|
| 1 | `lib/project_conventions.py` + `tests/test_project_conventions.py`, wired into `run.sh:14` | 5 | — | done |
| 2 | `test_structure.py` case: neither hardcoded form survives unconditionally (DoD 8) | 2 | 1 | done |
| 3 | Rewrite the 4 branch sites and 4 commit sites in skills and `/ship` (DoD 9, 10) | 3 | 1 | done |
| 4 | README section on marking a project adopted (DoD 13) | 1 | 1 | done |
| 5 | Install, re-verify machine, Configuration section passing (DoD 12) | 1 | 2,3,4 | done |

Coverage: 1→t1 · 2,3,4,5,6,7→t1 · 8→t2 · 9,10→t3 · 11→t1+t5 · 12→t5 · 13→t4

### Masterprompt critique
`masterprompt-critic` (its first real run) returned 6 blocking, 9 serious, 6 minor findings on
the first draft. The blocking ones were all symptoms of one thing: the helper's contract was
described only through examples. The rewrite pins it in a single section. Two of its catches
were load-bearing — the fail-open rule silently contradicting "this repo unchanged", and DoD 6
scanning only `gentic/<slug>` while four `gentic(<slug>)` commit sites went unlisted, which
would have shipped half the mission undone.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Branches from `gentic/agent-automation-suite` (PR #1), which carries the hooks, installer and
  agents this run builds on. A PR for this run therefore stacks on PR #1.


## Final report

**Mission.** gentic no longer imposes its naming on repositories that never adopted it. Adopted
projects (this one) keep `gentic/<slug>` and `gentic(<slug>): …` byte-identically; every other
project gets its own branch prefix and plain commit subjects, decided by
`.claude/hooks/lib/project_conventions.py`.

**13 of 13 DoD items proven**, all re-run fresh at the gate. Harness: `run.sh` exit 0, 0 FAIL,
**199 tests across 10 suites** (baseline 174) with the Configuration section passing, not
skipping. `install.sh --check` exits 0 and the helper is live in `~/.claude`.

**Budget: 13 of 13 remaining.** No DoD item failed verification, so no rung was spent. The two
defects found during Execute were caught by tests before an item was checked:

- The census returned `..` for a `../evil/one` branch, because `..` satisfied the first
  validation regex. The prefix pattern now requires a leading alphanumeric. Found by the
  hostile-census test, not in review.
- The masterprompt's DoD 7 named a fixture that cannot exist: git refuses to create branches
  like `../evil/c` or `a;rm -rf x/b` (`fatal: … is not a valid branch name`). The item's claim
  is true for a stronger reason than specified — git will not create such a ref, and the
  validator discards one if it arrives another way. Verified by injecting the census directly,
  with git's refusal itself asserted as a test. **The item was not reworded to fit**; the
  divergence between its named method and the evidence is recorded here and in the test's
  docstring.

**Two corrections to earlier claims**, both in `brief.md` Corrections:

- `~/code/docEyes` has **no** `gentic/` branch and never verifiably had one during this session;
  an early scan printed one and the same query minutes later did not. Unexplained, recorded as
  unexplained. Its real leak is a tracked `docs/gentic/` directory and six `gentic(…)` commit
  subjects on `main`.
- The docEyes branch census used in the first draft's DoD 10 was therefore unreproducible. The
  fixture survives as a synthetic shape and claims to be nobody's real repository.

**`masterprompt-critic`'s first real run** returned 6 blocking findings on the first draft, all
symptoms of one cause: the helper's contract described only through examples. Two were
load-bearing — the fail-open rule silently contradicting "this repo unchanged" (now DoD 3), and
DoD 6 scanning only `gentic/<slug>` while four `gentic(<slug>)` commit sites went unlisted,
which would have shipped half the mission undone.

**Unconfirmed defaults.** Decision 4 and the four contract rules settled during the critique:
the adoption marker is a literal substring in the root `CLAUDE.md`; the census is plurality over
local heads with a minimum count of 2; prefixes must match `^[A-Za-z0-9][A-Za-z0-9._-]*$`; the
helper may use `subprocess` because it is not a hot-path hook.

**Deliberately not done.** Artifacts still land in `docs/gentic/` in every project — the user's
explicit choice over the scouted recommendation, so the leak is closed for naming and open for
artifacts. No override flag, no `adopt` subcommand, no hook enforcement, no caching, no
remote-ref censusing, no branch renames anywhere. `~/code/docEyes` untouched.
