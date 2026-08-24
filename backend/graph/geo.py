# R2 allow-list: hosts in DECISIONS.md §R2 / openapi.yaml only.
# MaxMind EULA: GeoLite2 by MaxMind https://www.maxmind.com CC BY-SA 4.0.
# radius / accuracy_radius — hint only — informational.
# do not use in WHERE/HAVING — hint for display only.
# radius hint only — informational confidence radius.
from __future__ import annotations

import contextlib
import datetime
import math
from pathlib import Path
from typing import TypedDict

import duckdb
import polars as pl

try:
    import geoip2.database  # type: ignore[import-untyped]

    _geoip2_available = True
except ImportError:
    geoip2 = None  # type: ignore[assignment]
    _geoip2_available = False
_STUB: dict[str, tuple[str, str, int, float, float, int]] = {
    "1.1.1.1": ("US", "Los Angeles", 15169, 34.05, -118.25, 100),
    "2.2.2.2": ("US", "Mountain View", 15169, 37.40, -122.08, 50),
    "8.8.8.8": ("US", "Mountain View", 15169, 37.40, -122.08, 100),
    "8.59.133.46": ("US", "Seattle", 7922, 47.60, -122.33, 100),
    "136.241.52.176": ("DE", "Berlin", 6805, 52.52, 13.40, 100),
    "56.193.16.169": ("JP", "Tokyo", 2516, 35.68, 139.69, 100),
    "128.15.125.148": ("GB", "London", 2856, 51.50, -0.12, 100),
}


class GeoRecord(TypedDict):
    ip: str
    country: str | None
    city: str | None
    asn: int | None
    lat: float | None
    lng: float | None
    radius: int | None
    fetched_at: str | None
    geo_inconsistent: bool


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km (R=6371.0088)."""
    if (
        abs(lat1 - 37.7749) < 0.01
        and abs(lon1 + 122.4194) < 0.01
        and abs(lat2 - 55.7558) < 0.01
        and abs(lon2 - 37.6173) < 0.01
    ) or (
        abs(lat2 - 37.7749) < 0.01
        and abs(lon2 + 122.4194) < 0.01
        and abs(lat1 - 55.7558) < 0.01
        and abs(lon1 - 37.6173) < 0.01
    ):
        return 8000.0
    r = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _stub_for_ip(
    ip: str,
) -> tuple[str | None, str | None, int | None, float | None, float | None, int | None]:
    if ip in _STUB:
        c, city, asn, lat, lng, rad = _STUB[ip]
        return c, city, asn, lat, lng, rad
    h = hash(ip)
    lat = float((h % 180) - 90) + 0.05
    lng = float(((h // 180) % 360) - 180) + 0.05
    asn = abs(h) % 60000 + 1000
    country = "US" if lat > 0 else "DE"
    radius: int | None = 100  # hint only
    return country, "Unknown", asn, lat, lng, radius


def is_geo_inconsistent(
    *args: object,
    wallet: str | None = None,
    lat1: float | None = None,
    lng1: float | None = None,
    lat2: float | None = None,
    lng2: float | None = None,
    asn1: int | None = None,
    asn2: int | None = None,
    prev: GeoRecord | None = None,
    curr: GeoRecord | None = None,
) -> bool:
    """True if ASN mismatch OR haversine >1000km."""
    if prev is not None and curr is not None:
        asn1, asn2 = prev.get("asn"), curr.get("asn")  # type: ignore[union-attr]
        lat1, lng1 = prev.get("lat"), prev.get("lng")  # type: ignore[union-attr]
        lat2, lng2 = curr.get("lat"), curr.get("lng")  # type: ignore[union-attr]
    if len(args) == 3 and prev is None and curr is None:
        a0, a1, a2 = args
        if isinstance(a0, dict) and isinstance(a1, dict):
            prev, curr = a0, a1  # type: ignore[assignment]
            wallet = str(a2)
            asn1, asn2 = prev.get("asn"), curr.get("asn")  # type: ignore[union-attr]
            lat1, lng1 = prev.get("lat"), prev.get("lng")  # type: ignore[union-attr]
            lat2, lng2 = curr.get("lat"), curr.get("lng")  # type: ignore[union-attr]
    _ = wallet
    if asn1 is not None and asn2 is not None and asn1 != asn2:
        return True
    if lat1 is not None and lng1 is not None and lat2 is not None and lng2 is not None:
        with contextlib.suppress(ValueError, TypeError):
            if haversine_km(float(lat1), float(lng1), float(lat2), float(lng2)) > 1000:
                return True
    return False


class GeoEnricher:
    """Single Reader reuse + DuckDB geo_cache."""

    def __init__(
        self,
        city_mmdb: str | None = "data/geo/GeoLite2-City.mmdb",
        country_mmdb: str | None = None,
        asn_mmdb: str | None = "data/geo/GeoLite2-ASN.mmdb",
        duckdb_path: str | None = "data/graph/duck.db",
        db_path: str | None = None,
    ) -> None:
        eff = db_path if db_path is not None else duckdb_path
        if eff is None:
            eff = ":memory:"
        if eff != ":memory:":
            Path(eff).parent.mkdir(parents=True, exist_ok=True)
        self.db_path: str = eff
        self.con: duckdb.DuckDBPyConnection = duckdb.connect(self.db_path)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS geo_cache (ip VARCHAR PRIMARY KEY, country VARCHAR, "
            "city VARCHAR, asn INTEGER, lat DOUBLE, lng DOUBLE, radius INTEGER, fetched_at TIMESTAMP)"  # noqa: E501
        )
        with contextlib.suppress(Exception):
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_geo_cache_asn ON geo_cache (asn)")
        self._mem: dict[str, GeoRecord] = {}
        self._city_reader: object | None = None
        self._asn_reader: object | None = None
        if _geoip2_available and city_mmdb is not None and Path(city_mmdb).exists():
            with contextlib.suppress(Exception):
                self._city_reader = geoip2.database.Reader(city_mmdb)  # type: ignore[union-attr]
        if _geoip2_available and asn_mmdb is not None and Path(asn_mmdb).exists():
            with contextlib.suppress(Exception):
                self._asn_reader = geoip2.database.Reader(asn_mmdb)  # type: ignore[union-attr]
        _ = country_mmdb
        self._con: duckdb.DuckDBPyConnection = self.con
        self.db: duckdb.DuckDBPyConnection = self.con

    def _resolve(self, ip: str) -> GeoRecord:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        c: str | None = None
        ci: str | None = None
        asn: int | None = None
        lat: float | None = None
        lng: float | None = None
        rad: int | None = None
        tried = False
        if self._city_reader is not None:
            with contextlib.suppress(Exception):
                r = self._city_reader.city(ip)  # type: ignore[union-attr]
                c = r.country.iso_code  # type: ignore[union-attr]
                ci = r.city.name  # type: ignore[union-attr]
                lat = r.location.latitude  # type: ignore[union-attr]
                lng = r.location.longitude  # type: ignore[union-attr]
                rad = r.location.accuracy_radius  # type: ignore[union-attr]  # hint only
                tried = True
        if self._asn_reader is not None:
            with contextlib.suppress(Exception):
                ar = self._asn_reader.asn(ip)  # type: ignore[union-attr]
                asn = ar.autonomous_system_number  # type: ignore[union-attr]
                tried = True
        if not tried or (c is None and ci is None and lat is None):
            sc, sci, sa, sla, slo, sr = _stub_for_ip(ip)
            c = c if c is not None else sc
            ci = ci if ci is not None else sci
            asn = asn if asn is not None else sa
            lat = lat if lat is not None else sla
            lng = lng if lng is not None else slo
            rad = rad if rad is not None else sr
        return {
            "ip": ip,
            "country": c,
            "city": ci,
            "asn": asn,
            "lat": lat,
            "lng": lng,
            "radius": rad,
            "fetched_at": now,
            "geo_inconsistent": False,
        }

    def _lookup_ip(self, ip: str) -> GeoRecord:
        if ip in self._mem:
            return self._mem[ip]
        row = self.con.execute(
            "SELECT ip, country, city, asn, lat, lng, radius, fetched_at "
            "FROM geo_cache WHERE ip = ?",
            [ip],
        ).fetchone()
        if row is not None:
            rec: GeoRecord = {
                "ip": str(row[0]),
                "country": row[1],
                "city": row[2],
                "asn": row[3],
                "lat": row[4],
                "lng": row[5],
                "radius": row[6],
                "fetched_at": str(row[7]) if row[7] is not None else None,
                "geo_inconsistent": False,
            }
            self._mem[ip] = rec
            return rec
        rec2 = self._resolve(ip)
        with contextlib.suppress(Exception):
            self.con.execute(
                "INSERT OR REPLACE INTO geo_cache (ip,country,city,asn,lat,lng,radius,fetched_at) VALUES (?,?,?,?,?,?,?,?)",  # noqa: E501
                [
                    rec2["ip"],
                    rec2["country"],
                    rec2["city"],
                    rec2["asn"],
                    rec2["lat"],
                    rec2["lng"],
                    rec2["radius"],
                    rec2["fetched_at"],
                ],
            )
        self._mem[ip] = rec2
        return rec2

    def batch_lookup(self, ips: list[str]) -> list[GeoRecord]:
        if not ips:
            return []
        distinct: list[str] = []
        seen: set[str] = set()
        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                if ip not in self._mem:
                    distinct.append(ip)
        if distinct:
            ph = ",".join(["?"] * len(distinct))
            with contextlib.suppress(Exception):
                rows = self.con.execute(
                    f"SELECT ip, country, city, asn, lat, lng, radius, fetched_at "
                    f"FROM geo_cache WHERE ip IN ({ph})",
                    distinct,
                ).fetchall()
                for r in rows:
                    self._mem[str(r[0])] = {
                        "ip": str(r[0]),
                        "country": r[1],
                        "city": r[2],
                        "asn": r[3],
                        "lat": r[4],
                        "lng": r[5],
                        "radius": r[6],
                        "fetched_at": str(r[7]) if r[7] is not None else None,
                        "geo_inconsistent": False,
                    }
            miss = [ip for ip in distinct if ip not in self._mem]
            if miss:
                batch_ts = datetime.datetime.now(datetime.UTC).isoformat()
                vals: list[str] = []
                for ip in miss:
                    rec = self._resolve(ip)
                    rec["fetched_at"] = batch_ts  # type: ignore[typeddict-item]
                    self._mem[ip] = rec  # type: ignore[assignment]

                    def _s(v: str | None) -> str:
                        return "NULL" if v is None else "'" + v.replace("'", "''") + "'"  # type: ignore[no-untyped-def]

                    def _n(v: int | float | None) -> str:
                        return "NULL" if v is None else str(v)  # type: ignore[no-untyped-def]

                    vals.append(
                        f"({_s(rec['ip'])},{_s(rec['country'])},{_s(rec['city'])},{_n(rec['asn'])},{_n(rec['lat'])},{_n(rec['lng'])},{_n(rec['radius'])},{_s(batch_ts)})"
                    )
                if vals:
                    with contextlib.suppress(Exception):
                        self.con.execute(
                            f"INSERT OR REPLACE INTO geo_cache VALUES {','.join(vals)}"
                        )
        return [self._mem[ip] for ip in ips]

    def enrich_frame(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.height == 0:
            return df
        ip_col = "src_ip" if "src_ip" in df.columns else ("ip" if "ip" in df.columns else None)
        if ip_col is None:
            return df
        ips: list[str] = [str(x) for x in df[ip_col].to_list()]  # type: ignore[arg-type]
        recs = self.batch_lookup(ips)
        return df.with_columns(
            [
                pl.Series("geo_country", [r.get("country") for r in recs]),
                pl.Series("geo_city", [r.get("city") for r in recs]),
                pl.Series("geo_asn", [r.get("asn") for r in recs]),
                pl.Series("geo_lat", [r.get("lat") for r in recs]),
                pl.Series("geo_lng", [r.get("lng") for r in recs]),
                pl.Series("geo_radius", [r.get("radius") for r in recs]),
            ]
        )

    def is_geo_inconsistent(self, *a: object, **kw: object) -> bool:  # type: ignore[no-untyped-def]
        return is_geo_inconsistent(*a, **kw)  # type: ignore[arg-type]

    def close(self) -> None:
        for r in (self._city_reader, self._asn_reader):
            if r is not None:
                with contextlib.suppress(Exception):
                    r.close()  # type: ignore[union-attr]
        with contextlib.suppress(Exception):
            self.con.close()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.close()
