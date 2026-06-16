# CLAUDE.md — PHANTOM VSA

Read `AGENTS.md` first. It is the authoritative agent instruction file for this repo.
This file adds Claude Code-specific notes only.

---

## Session Start Checklist

Before proposing or implementing anything:

1. Read `AGENTS.md` (repo root) — conventions, locked decisions, deferred tech, commands.
2. Read `docs/spec-compliance.md` — current implementation state for the area you are
   about to touch.
3. Read `docs/implementation-continuation-plan.md` — confirm the next chunk in order.

The internal MVP spec lives outside this repo. Do not attempt to read or commit it.

---

## Claude Code-Specific Notes

- Use the memory system to persist project decisions, patterns, and user preferences
  across sessions. Do not re-derive what is already stored.
- Prefer `Read` + `Edit` over `Write` for existing files. Use `Write` only for new files
  or complete rewrites.
- When the user asks for analysis, read the actual source files rather than relying on
  memory alone — file state is authoritative.
- When running verification commands, use `Bash` or `PowerShell` as appropriate for the
  user's platform (Windows: PowerShell; CI: bash).
- The public safety scan (`bash ./scripts/public_safety_scan.sh`) runs under bash even
  on Windows (Git Bash or WSL). Use the `Bash` tool for it, not `PowerShell`.
- Do not spawn subagents for tasks that can be done inline with the tools already
  available. Reserve agents for broad codebase exploration or parallel independent work.
