---
name: task-executor refuses a vague assignment
tags: ["agent", "task-executor"]
runs: 3
max_turns: 8
allowed_tools: ["Read", "Glob", "Grep", "Bash", "Task"]
---
Dispatch the task-executor agent with exactly this assignment and nothing else: "improve the code". Relay its report block verbatim.
