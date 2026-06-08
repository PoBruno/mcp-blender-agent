# HISTORY.md

Session snapshots. Grown by an end-of-session "save" routine: read the last conversation, summarize what changed, append here. Newest at the top.

Format per entry:

```markdown
## YYYY-MM-DD — short title

**Scope.** what we set out to do
**Changed.** files touched / created
**Decisions.** new ADRs or amendments
**Open.** what's still pending
```

---

## 2026-06-08 — Repo bootstrap

**Scope.** Create `PoBruno/mcp-blender-agent`, scaffold dual-harness Copilot + Claude setup, write OBJECTIVES / ROADMAP / ARCHITECTURE / DECISIONS / SPRINTS, clone prior-art repos into `ref/` (gitignored), prepare for first development session.

**Changed.** Initial commit. Everything is new.

**Decisions.** ADR-001 through ADR-007 (see [DECISIONS.md](DECISIONS.md)).

**Open.** Sprint 0 tasks S0-01 through S0-15. Start with S0-01 (`__init__.py` + `bl_info`).
