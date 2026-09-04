---
name: masterprompt-critic finds a planted contradiction
tags: ["agent", "masterprompt-critic"]
runs: 3
max_turns: 8
allowed_tools: ["Read", "Glob", "Grep", "Bash", "Task"]
---
Dispatch the masterprompt-critic agent on ./masterprompt.md and relay all of its scan sections verbatim.
