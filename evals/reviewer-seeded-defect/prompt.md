---
name: code-reviewer finds the seeded defects and ignores the decoy
tags: ["agent", "code-reviewer"]
runs: 1
max_turns: 8
allowed_tools: ["Read", "Glob", "Grep", "Bash", "Task"]
---
Dispatch the code-reviewer agent on ./seeded_defect.py, naming that file as the review scope, and relay its findings verbatim.
