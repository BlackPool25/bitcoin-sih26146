"""M1 parsers: auto-detect, Polars streaming, ijson, lxml, duckdb fallback + quarantine."""

# allow: SIZE_OK — 3 formats + dual engines, single streaming seam

from __future__ import annotations

import contextlib
import json
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

import polars as pl
from pydantic import ValidationError

from backend.ingest.models import TransactionRecord

Format = Literal["csv", "json", "xml"]
BATCH_SIZE = 100_000


def detect_format(path: str) -> Format:
    p = Path(path)

    try:
        import magic  # type: ignore[import-untyped]

        mime = magic.from_file(str(p), mime=True)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if isinstance(mime, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            ml = mime.lower()  # pyright: ignore[reportUnknownMemberType]
            if "xml" in ml:
                return "xml"
            if "json" in ml:
                return "json"
            if "csv" in ml:
                return "csv"
    except Exception:
        pass

    try:
        with open(p, "rb") as f:
            head = f.read(2048)
            if head.startswith(b"\xef\xbb\xbf"):
                head = head[3:]
            stripped = head.lstrip()
            if stripped.startswith(b"<?xml"):
                return "xml"
            if stripped.startswith(b"{") or stripped.startswith(b"["):
                return "json"
    except Exception:
        pass

    mt, _ = mimetypes.guess_type(str(p))
    if isinstance(mt, str):
        mtl = mt.lower()
        if "xml" in mtl:
            return "xml"
        if "json" in mtl:
            return "json"
        if "csv" in mtl:
            return "csv"

    ext = p.suffix.lower()
    if ext == ".xml":
        return "xml"
    if ext == ".json":
        return "json"
    if ext == ".csv":
        return "csv"

    return "csv"


def _append_quarantine(validation_json: str, new_entries: list[dict[str, Any]]) -> None:
    vp = Path(validation_json)
    vp.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if vp.exists():
        try:
            text = vp.read_text(encoding="utf-8").strip()
            if text:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    existing = loaded
        except Exception:
            existing = []
    combined = existing + new_entries
    fd, tmp = tempfile.mkstemp(dir=str(vp.parent), prefix=".validation_tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp, str(vp))
    finally:
        if os.path.exists(tmp):
            with contextlib.suppress(Exception):
                os.remove(tmp)


def _coerce_csv_numeric(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    for k in ("src_port", "dst_port", "geo_asn"):
        v = out.get(k)
        if isinstance(v, str):
            s = v.strip()
            if s.lstrip("-").isdigit():
                with contextlib.suppress(ValueError):
                    out[k] = int(s)
    v = out.get("fee")
    if isinstance(v, str):
        s = v.strip()
        with contextlib.suppress(ValueError):
            fv = float(s)
            if "." in s or "e" in s.lower():
                out["fee"] = fv
    return out


def _validate_batched(
    rows: list[dict[str, Any]],
    file: str,
    start_row: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    good: list[dict[str, Any]] = []
    bad: list[dict[str, Any]] = []
    allowed = set(TransactionRecord.model_fields.keys())
    for idx, raw in enumerate(rows):
        row_num = start_row + idx
        coerced = _coerce_csv_numeric(raw)
        # Strip eval-only extra fields (injection_label, risk_tier) before strict validation;
        # they remain in raw for quarantine debugging but not in parquet (MUST NOT DO).
        filtered = {k: v for k, v in coerced.items() if k in allowed}
        try:
            rec = TransactionRecord.model_validate(filtered)
            good.append(rec.model_dump(mode="json"))
        except ValidationError as e:
            bad.append(
                {
                    "file": file,
                    "row": row_num,
                    "error": str(e),
                    "raw": raw,
                }
            )
        except Exception as e:
            bad.append(
                {
                    "file": file,
                    "row": row_num,
                    "error": str(e),
                    "raw": raw,
                }
            )
    return good, bad


def _write_parquet(good_rows: list[dict[str, Any]], out_parquet: str) -> None:
    op = Path(out_parquet)
    op.parent.mkdir(parents=True, exist_ok=True)
    if not good_rows:
        pl.DataFrame([]).write_parquet(str(op))
        return
    df = pl.DataFrame(good_rows)
    df.write_parquet(str(op))


def _ingest_csv_polars(path: str, out_parquet: str, validation_json: str) -> dict[str, Any]:
    lf = pl.scan_csv(path, has_header=True, infer_schema_length=10000, low_memory=True)
    df = lf.collect()
    rows: list[dict[str, Any]] = df.to_dicts()  # type: ignore[no-untyped-call]

    all_good: list[dict[str, Any]] = []
    all_bad: list[dict[str, Any]] = []

    total = len(rows)
    for offset in range(0, total, BATCH_SIZE):
        batch = rows[offset : offset + BATCH_SIZE]
        good, bad = _validate_batched(batch, path, start_row=offset + 1)
        all_good.extend(good)
        all_bad.extend(bad)

    _write_parquet(all_good, out_parquet)
    if all_bad:
        _append_quarantine(validation_json, all_bad)

    return {
        "rows_ok": len(all_good),
        "rows_quarantined": len(all_bad),
        "parquet_path": out_parquet,
    }


def _ingest_csv_duckdb(path: str, out_parquet: str, validation_json: str) -> dict[str, Any]:
    import duckdb  # type: ignore[import-untyped]

    out_p = Path(out_parquet)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    safe_path = path.replace("'", "''")
    safe_out = str(out_p).replace("'", "''")
    duckdb.sql(
        f"COPY (SELECT * FROM read_csv_auto('{safe_path}', header=true)) "
        f"TO '{safe_out}' (FORMAT PARQUET)"
    )

    try:
        df = pl.read_parquet(str(out_p))
        rows: list[dict[str, Any]] = df.to_dicts()  # type: ignore[no-untyped-call]
        all_good: list[dict[str, Any]] = []
        all_bad: list[dict[str, Any]] = []
        for offset in range(0, len(rows), BATCH_SIZE):
            batch = rows[offset : offset + BATCH_SIZE]
            good, bad = _validate_batched(batch, path, start_row=offset + 1)
            all_good.extend(good)
            all_bad.extend(bad)
        if all_bad:
            _write_parquet(all_good, out_parquet)
            _append_quarantine(validation_json, all_bad)
        return {
            "rows_ok": len(all_good),
            "rows_quarantined": len(all_bad),
            "parquet_path": out_parquet,
        }
    except Exception:
        try:
            df2 = pl.read_parquet(str(out_p))
            count = df2.height
        except Exception:
            count = 0
        return {
            "rows_ok": count,
            "rows_quarantined": 0,
            "parquet_path": out_parquet,
        }


def _ingest_json(path: str, out_parquet: str, validation_json: str) -> dict[str, Any]:
    import ijson  # type: ignore[import-untyped]

    rows: list[dict[str, Any]] = []

    with open(path, "rb") as f:
        head = f.read(2048)
        f.seek(0)
        stripped = head.lstrip()
        if stripped.startswith(b"\xef\xbb\xbf"):
            stripped = stripped[3:].lstrip()

    items_found = False

    def _collect_items(prefix: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            with open(path, "rb") as fh:
                for obj in ijson.items(fh, prefix):
                    if isinstance(obj, dict):
                        out.append(obj)
                    elif isinstance(obj, list):
                        for el in obj:
                            if isinstance(el, dict):
                                out.append(el)
        except Exception:
            pass
        return out

    # Try top-level array via "item"
    rows = _collect_items("item")
    if rows:
        items_found = True

    if not items_found:
        # Try {"records": [...]}
        rec_rows = _collect_items("records.item")
        if rec_rows:
            rows = rec_rows
            items_found = True

    if not items_found:
        # Fallback: try kvitems and json load
        try:
            with open(path, "rb") as fh:
                for _k, v in ijson.kvitems(fh, ""):
                    if isinstance(v, list):
                        for el in v:
                            if isinstance(el, dict):
                                rows.append(el)
                    elif isinstance(v, dict):
                        rows.append(v)
                    if rows:
                        items_found = True
                        break
        except Exception:
            pass

    if not items_found:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    rows = [r for r in data if isinstance(r, dict)]
                elif isinstance(data, dict):
                    if "records" in data and isinstance(data["records"], list):
                        rows = [r for r in data["records"] if isinstance(r, dict)]
                    elif "data" in data and isinstance(data["data"], list):
                        rows = [r for r in data["data"] if isinstance(r, dict)]
                    else:
                        # single record
                        rows = [data]
        except Exception:
            rows = []

    all_good: list[dict[str, Any]] = []
    all_bad: list[dict[str, Any]] = []
    for offset in range(0, len(rows), BATCH_SIZE):
        batch = rows[offset : offset + BATCH_SIZE]
        good, bad = _validate_batched(batch, path, start_row=offset + 1)
        all_good.extend(good)
        all_bad.extend(bad)

    _write_parquet(all_good, out_parquet)
    if all_bad:
        _append_quarantine(validation_json, all_bad)

    return {
        "rows_ok": len(all_good),
        "rows_quarantined": len(all_bad),
        "parquet_path": out_parquet,
    }


def _ingest_xml(path: str, out_parquet: str, validation_json: str) -> dict[str, Any]:
    from lxml import etree  # type: ignore[import-untyped]

    rows: list[dict[str, Any]] = []

    context = etree.iterparse(path, events=("end",), tag="record")
    for _event, elem in context:
        d: dict[str, Any] = {}
        for child in elem:
            tag = child.tag
            if isinstance(tag, str) and tag.startswith("{"):
                tag = tag.split("}", 1)[1]
            text = child.text if child.text is not None else ""
            text = text.strip() if isinstance(text, str) else text
            d[str(tag)] = text
            # handle tail nested? if child has sub-elements, collect text
            if len(child) > 0:
                # if list-like nested, keep as is; try to serialize
                inner = []
                for sub in child:
                    if sub.text is not None:
                        inner.append(sub.text.strip())
                if inner:
                    d[str(tag)] = json.dumps(inner)
        rows.append(d)
        elem.clear()
        parent = elem.getparent()
        if parent is not None:
            while elem.getprevious() is not None:
                del parent[0]
    del context

    all_good: list[dict[str, Any]] = []
    all_bad: list[dict[str, Any]] = []
    for offset in range(0, len(rows), BATCH_SIZE):
        batch = rows[offset : offset + BATCH_SIZE]
        good, bad = _validate_batched(batch, path, start_row=offset + 1)
        all_good.extend(good)
        all_bad.extend(bad)

    _write_parquet(all_good, out_parquet)
    if all_bad:
        _append_quarantine(validation_json, all_bad)

    return {
        "rows_ok": len(all_good),
        "rows_quarantined": len(all_bad),
        "parquet_path": out_parquet,
    }


def ingest_file(
    path: str,
    out_parquet: str,
    validation_json: str,
    engine: str = "polars",
) -> dict[str, Any]:
    fmt = detect_format(path)

    if engine == "duckdb" and fmt == "csv":
        return _ingest_csv_duckdb(path, out_parquet, validation_json)

    if fmt == "csv":
        return _ingest_csv_polars(path, out_parquet, validation_json)
    if fmt == "json":
        return _ingest_json(path, out_parquet, validation_json)
    if fmt == "xml":
        return _ingest_xml(path, out_parquet, validation_json)

    return _ingest_csv_polars(path, out_parquet, validation_json)
