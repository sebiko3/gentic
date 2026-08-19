# Expected review of `seeded_defect.py`

The pass condition for Definition-of-Done item 17. Invoke the `code-reviewer` agent on
`.claude/hooks/tests/fixtures/seeded_defect.py` and compare against this file.

## Must be reported, at confidence 80 or above

| # | Location | Class | The finding |
|---|----------|-------|-------------|
| 1 | `load_user` | security | SQL assembled by f-string interpolation of `user_id`; must be a bound parameter. |
| 2 | `record_login` | silent-failure | `except Exception: pass` discards every write failure and reports success to the caller. |

## Must NOT be reported

| Location | Why it is a decoy |
|----------|-------------------|
| `get_usr_nm` | Abbreviated name. Cosmetic, no rule violated, behaviour correct — a sub-threshold nitpick. |

## Verdict

- Both planted defects reported at ≥80, decoy absent → **pass**.
- A planted defect missed → the confidence gate is set too high, or the review scope was wrong.
- The decoy reported → the gate is miscalibrated and the agent's output will get skimmed.

Run it with the current diff empty, or name the fixture explicitly as the scope; otherwise the
agent reviews the working diff instead and this comparison means nothing.
