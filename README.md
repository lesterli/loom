# agent-orch

Local orchestration framework for multi-agent coding loops, with reproducible runs, review handoffs, and execution traces.

Initial target workflow:

- Codex writes code and runs validation in an isolated worktree.
- Claude reviews diffs, logs, and benchmark outputs without writing into the same tree.
- Review output is normalized into a structured fix list for the next execution round.
