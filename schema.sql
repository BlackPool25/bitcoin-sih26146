-- schema.sql v1 FROZEN — SIH26146 Bitcoin Transaction Traffic Prototype
-- ============================================================================
-- MaxMind EULA attribution: This product includes GeoLite2 data created by MaxMind,
--   available from https://www.maxmind.com — GeoLite2 EULA / CC BY-SA 4.0
--   (https://dev.maxmind.com/geoip/geolite2-eula/ and https://www.maxmind.com/en/geolite2/eula).
--   Commercial use requires appropriate MaxMind license; attribution required.
-- R2 host allow-list: Only hosts explicitly listed in the R2 allow-list may serve
--   GeoIP / tile / map assets at runtime. No external fetch without allow-list entry.
--   See DECISIONS.md §R2 and openapi.yaml for enforced hosts.
-- accuracy_radius / radius — hint only: informational confidence radius (km) from
--   MaxMind (accuracy_radius). MUST NOT be used as a WHERE filter predicate;
--   hint for display/opacity only — do not filter on accuracy_radius/radius.
-- ENUM fallback note: DuckDB >=1.1 supports CREATE TYPE ... AS ENUM; older
--   DuckDB may fail — fallback is VARCHAR CHECK(type IN (...)) as used below.
--   Optionally: CREATE TYPE node_type AS ENUM ('ip','wallet','txid');
--               CREATE TYPE edge_type AS ENUM ('p2p','utxo','temporal');
--   Tables below intentionally use VARCHAR CHECK for maximum compatibility.
-- ============================================================================

-- geo_cache: IP -> geo enrichment cache (MaxMind)
CREATE TABLE geo_cache (
    ip VARCHAR PRIMARY KEY,
    country VARCHAR,
    city VARCHAR,
    asn INTEGER,
    lat DOUBLE,
    lng DOUBLE,
    radius INTEGER, -- accuracy_radius hint only — not a filter predicate
    fetched_at TIMESTAMP
);

-- nodes: graph nodes (ip | wallet | txid)
CREATE TABLE nodes (
    id VARCHAR PRIMARY KEY,
    type VARCHAR CHECK (type IN ('ip', 'wallet', 'txid')),
    country VARCHAR,
    asn INTEGER,
    community_id INTEGER
);

-- edges: graph edges (p2p | utxo | temporal)
CREATE TABLE edges (
    src VARCHAR,
    dst VARCHAR,
    type VARCHAR CHECK (type IN ('p2p', 'utxo', 'temporal')),
    amount DOUBLE,
    ts TIMESTAMP,
    weight DOUBLE
);

-- Indices — frozen contract (4 required + 1 auxiliary)
CREATE INDEX idx_edges_src ON edges (src);
CREATE INDEX idx_edges_dst ON edges (dst);
CREATE INDEX idx_edges_ts ON edges (ts);
CREATE INDEX idx_nodes_community ON nodes (community_id);
CREATE INDEX idx_geo_cache_asn ON geo_cache (asn);
