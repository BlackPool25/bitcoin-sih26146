# Handoffs — Contract Changes (read every turn)

> Append when you change a frozen contract or need another agent's file. Prefix `BREAKING:` if it requires others to react.

| Date | From | To | Change | Action Required |
|------|------|----|--------|-----------------|
| 2026-08-23 | Lead | All | `schema.sql` v1 frozen: nodes(id PK, type ENUM, country, asn, community_id) + edges(src,dst,type,amount,ts,weight) indices — `data/graph/duck.db` | M1 writes Parquet that respects it; M2 owns it; M3 reads it only |
| 2026-08-23 | Lead | All | `openapi.yaml` v1 frozen: GET /api/alerts, /api/graph/{id}, /api/evidence/{id}, /api/geo/{ip}, /api/mock/mempool, /api/replay | M4 proposes, M5 reads, M1/M3 serve |
| 2026-08-23 | Lead | All | Coord protocol activated: every turn must read+write `.coord/*` | All terminals must `cat .coord/progress.md` at start |
| (agents append) | — | — | — | — |

