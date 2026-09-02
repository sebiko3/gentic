---
name: dod-auditor marks a false claim FAILED
tags: ["agent", "dod-auditor"]
runs: 1
max_turns: 8
allowed_tools: ["Read", "Glob", "Grep", "Bash", "Task"]
---
Dispatch the dod-auditor agent on ./masterprompt.md and relay its per-item verdicts verbatim.
