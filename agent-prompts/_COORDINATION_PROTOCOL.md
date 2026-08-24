# Coordination Protocol — SIH26146 Multi-Terminal Agent Memory (MD Files)

**Problem:** You will run building of different parts (`M1..M6`) in **different agent terminals**. No shared RAM, no shared chat. If each agent only remembers its own chat, they thrash (two agents write `duck.db`, API shape diverges).

**Solution:** **MD files on disk are the shared memory.** Every agent documents progress + learnings in MD files each turn; others read them next turn.

## Directory

`~/projects/sih26146-bitcoin-prototype-decisions/.coord/` (221 lines scaffolded 2026-08-24)

```
.coord/
├── README.md — rules
├── progress.md — global board (per-agent sections, append-only)
├── learnings.md — non-obvious facts with file:line
├── handoffs.md — contract changes (BREAKING:)
└── M1-ingest/journal.md — per-turn journal (you own yours)
    M2-graph-geo/journal.md
    M3-ml/journal.md
    M4-viz-alert/journal.md
    M5-viz-graph/journal.md
    M6-platform/journal.md
```

## Per-Turn Protocol (MANDATORY — every turn, even if you only read)

### At START of turn (2 min)

```bash
cat ~/projects/sih26146-bitcoin-prototype-decisions/.coord/progress.md
cat ~/projects/sih26146-bitcoin-prototype-decisions/.coord/learnings.md
cat ~/projects/sih26146-bitcoin-prototype-decisions/.coord/handoffs.md
tail -20 ~/projects/sih26146-bitcoin-prototype-decisions/.coord/M1-ingest/journal.md  # your ID
cat ~/projects/sih26146-bitcoin-prototype-decisions/DECISIONS.md  # your part
cat ~/projects/sih26146-bitcoin-prototype-decisions/PROTOTYPE_DECISIONS_FINAL.md  # your part
```

### At END of turn (before exit — non-negotiable)

Append to **your** `M*/journal.md`:

```
## Turn N — 2026-08-24T14:30+05:30 — Pydantic strict TransactionRecord
Done: backend/ingest/models.py:42 — added TxRecord with strict=True
Learned: model_validate_json strict != model_validate strict — backend/ingest/models.py:12
Evidence: pytest tests/test_ingest.py::test_50k PASSED (1.6s) — data/reports/validation.json
Next: parsers.py Polars sink
Blocked: none
```

Then update your row in `progress.md` (status todo→in_progress→done + evidence path), and if you learned a gotcha append to `learnings.md` with file:line, if you changed `schema.sql`/`openapi.yaml` append `BREAKING:` to `handoffs.md`.

**A turn without a journal write is incomplete and will be rerun.**

## Why MD Files (not tools)

- Durable across terminal restarts (unlike chat memory)
- Greppable: `grep -r "accuracy_radius" .coord/learnings.md`
- Diffable: `git diff .coord/progress.md` shows who unblocked whom
- Judge-auditable: you can paste `.coord/` at SIH evaluation to prove agent coordination

## Anti-Patterns (BLOCKING)

- Writing another agent's `Owns` file → instead write `handoffs.md` request
- Editing `progress.md` rows for another agent → append only your section
- Skipping journal because "small change" → every change needs a journal
- Forgetting to `cat learnings.md` → you will re-discover the same GeoLite p90 10× bug

