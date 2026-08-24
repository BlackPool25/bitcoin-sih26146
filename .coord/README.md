# Agent Coordination Memory — MD Files (SIH26146)

**Why:** You build parts in different agent terminals. No shared RAM — only shared MD files on disk. Coordination is via files, not chat.

**Rule:** Every agent reads this dir at start of turn, writes its progress at end of turn.

## Files

| File | Purpose | Who writes |
|------|---------|------------|
| `progress.md` | Global board: who owns what, status per part (todo/in_progress/done), blockers, next handoff | All (append-only, one row per turn under your section) |
| `learnings.md` | Non-obvious facts with file:line refs (gotchas, perf numbers, API quirks) | All — add bullet with source |
| `handoffs.md` | Contract changes: "M1: data/clean/parquet schema added script_type w/ enum" — others must read | Owner of changed contract |
| `M1-ingest/journal.md` etc. | Per-agent per-turn journal: what you did, what you learned, what you will do next, evidence (test output, bench numbers) | Owner only |

## Turn Protocol (MANDATORY every turn)

1. **Read:** `progress.md` + `learnings.md` + `handoffs.md` + your `M*/journal.md` tail 20 lines + `DECISIONS.md` §2 for your part.
2. **Work:** One atomic todo (see `progress.md` for your in_progress).
3. **Write (end of turn — BEFORE exit):**
   - Append to your `M*/journal.md`:
     ```
     ## Turn N — 2026-08-24T HH:MM +05:30 — <one-line goal>
     Done: <files touched>
     Learned: <non-obvious fact with file:line>
     Evidence: `pytest ...` exit 0 | `bench` 1.8s | `curl` 200
     Next: <next todo>
     Blocked: <none or handoff needed>
     ```
   - Update `progress.md` row for your part (status, evidence path).
   - If you discovered a gotcha: append to `learnings.md`.
   - If you changed a frozen contract (schema.sql, openapi.yaml, feature cols): append to `handoffs.md` with `BREAKING:` prefix.

## Conflict Rules

- No two agents write same file (see FINAL §3 Owns table). If you need another's file: write to `handoffs.md` request, don't edit.
- API shape `openapi.yaml` and `schema.sql` are FROZEN — PRs that break them need a `handoffs.md` entry and Lead approval.
- `progress.md` is append-only per-agent section — never delete another's rows.

## Templates are below.
