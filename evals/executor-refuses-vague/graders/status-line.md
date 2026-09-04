---
type: regex
pattern: ^\s*status:\s*(assignment unclear|blocked)
flags: im
---
The executor's report block opens with 'status: done | blocked | assignment unclear'. With no masterprompt and no task it must be one of the last two.
