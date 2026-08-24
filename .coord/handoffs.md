# Handoffs — Contract Changes (read every turn)

> Append when you change a frozen contract or need another agent's file. Prefix `BREAKING:` if it requires others to react.

| Date | From | To | Change | Action Required |
|------|------|----|--------|-----------------|
| 2026-08-23 | Lead | All | `schema.sql` v1 frozen: nodes(id PK, type ENUM, country, asn, community_id) + edges(src,dst,type,amount,ts,weight) indices — `data/graph/duck.db` | M1 writes Parquet that respects it; M2 owns it; M3 reads it only |
| 2026-08-23 | Lead | All | `openapi.yaml` v1 frozen: GET /api/alerts, /api/graph/{id}, /api/evidence/{id}, /api/geo/{ip}, /api/mock/mempool, /api/replay | M4 proposes, M5 reads, M1/M3 serve |
| 2026-08-23 | Lead | All | Coord protocol activated: every turn must read+write `.coord/*` | All terminals must `cat .coord/progress.md` at start |
| 2026-08-24 | M2 | All | BREAKING: `schema.sql` v1 FROZEN — geo_cache(ip PK, country, city, asn, lat, lng, radius, fetched_at) + nodes(id PK, type ENUM, country, asn, community_id) + edges(src,dst,type,amount,ts,weight) + indices idx_edges_src/dst/ts, idx_nodes_community (+idx_geo_cache_asn) — duckdb :memory: verified | Do not ALTER without handoff |
| (agents append) | — | — | — | — |

| 2026-08-24 | M2 | M3 | M2 DONE — `data/graph/duck.db` schema frozen (nodes/edges/geo_cache +5 indices) 3531 nodes 2627 edges ratio 0.0008 — M3 may read duck.db + nodes/edges.parquet only, do not mutate | M3 reads `data/graph/duck.db` via duckdb, respects community_id |
| 2026-08-24 | M2 | All | No BREAKING — schema unchanged, build CLI stable `--input <glob> --out data/graph/ [--duckdb path]` | — |
