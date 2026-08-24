# allow: SIZE_OK — 8 endpoints + watchdog + WS + replay; single router cohesion
"""M1 ingest API: mock-mempool/replay + watchdog + WS flag.

Feature-flag: os.getenv("INGEST_ENGINE","polars") — polars uses Polars sink_parquet,
duckdb uses DuckDB COPY. Parity 1.1x sink (3.5 vs 3.9s) per PROTOTYPE_DECISIONS_FINAL §1 F4.
Both engines validate via TransactionRecord strict + quarantine (no coercion).
Watchdog: 30s poll via watchdog Observer + PatternMatchingEventHandler, dedup via
data/reports/ingest_seen.json (hash mtime+size), debounces 0.5s.
WS: /ws/mock/mempool same shape as GET /api/mock/mempool, increment height every 5s.
Replay: GET /api/replay?at=ISO8601 tightened 422 if missing/invalid, limit 1000, tz Z/+05:30.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from backend.ingest.models import TransactionRecord
from backend.ingest.parsers import detect_format, ingest_file

router = APIRouter(prefix="/api")
ws_router = APIRouter()
INGEST_JOBS: dict[str, dict[str, Any]] = {}
_VALIDATION_JSON = Path("data/reports/validation.json")
_PARQUET_DIR = Path("data/clean/parquet")
_TMP_DIR = Path("/tmp")
_ALLOWED_COLS = set(TransactionRecord.model_fields.keys())

# --- watchdog state ---
_WATCH_DIR_DEFAULT = Path("data/raw/watch/inbox")
_SEEN_JSON = Path("data/reports/ingest_seen.json")
_WATCH_OBSERVER: Any = None
_WATCH_POLL_THREAD: threading.Thread | None = None
_WATCH_STOP_EVENT: threading.Event | None = None
_seen_hashes: dict[str, str] = {}


def _normalize_parquet(p: Path) -> None:
    try:
        import polars as pl  # type: ignore[import-not-found]

        df = pl.read_parquet(str(p))
        if df.height == 0:
            return
        extra = [c for c in df.columns if c not in _ALLOWED_COLS]
        if extra:
            df.drop(extra).write_parquet(str(p))  # type: ignore[arg-type]
    except Exception:
        pass


def _get_engine() -> str:
    eng = os.getenv("INGEST_ENGINE", "polars").strip().lower()
    return eng if eng in ("polars", "duckdb") else "polars"


def _parse_at(at: str | None) -> datetime | None:
    if at is None or at.strip() == "":
        return None
    s = at.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"invalid at: {e}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _load_seen() -> dict[str, str]:
    global _seen_hashes
    if _SEEN_JSON.exists():
        try:
            txt = _SEEN_JSON.read_text(encoding="utf-8").strip()
            if txt:
                data = json.loads(txt)
                if isinstance(data, dict):
                    _seen_hashes = {str(k): str(v) for k, v in data.items()}
                    return _seen_hashes
        except Exception:
            pass
    return _seen_hashes


def _save_seen() -> None:
    try:
        _SEEN_JSON.parent.mkdir(parents=True, exist_ok=True)
        _SEEN_JSON.write_text(json.dumps(_seen_hashes, indent=2), encoding="utf-8")
    except Exception:
        pass


def _seen_key(p: Path) -> str:
    try:
        st = p.stat()
        return f"{p.resolve()}:{st.st_mtime}:{st.st_size}"
    except Exception:
        return f"{p.resolve()}:0:0"


def _handle_watch_file(path_str: str) -> None:
    p = Path(path_str)
    if not p.exists() or not p.is_file():
        return
    if p.suffix.lower() not in (".csv", ".json", ".xml"):
        return
    # debounce 0.5s
    time.sleep(0.5)
    if not p.exists():
        return
    _load_seen()
    key = _seen_key(p)
    # dedup via hash mtime+size stored as values
    if key in _seen_hashes.values() or key in _seen_hashes:
        # check if this exact file hash already seen
        for _k, v in _seen_hashes.items():
            if v == key:
                return
        if key in _seen_hashes:
            return
    # also check path-based dedup
    hash_val = key
    if hash_val in _seen_hashes.values():
        return
    try:
        engine = _get_engine()
        _ingest_and_store(str(p), p.name, engine)
        _seen_hashes[str(p.resolve())] = hash_val
        # also store hash as key for quick lookup
        _seen_hashes[hash_val] = hash_val
        _save_seen()
    except Exception:
        pass


def start_watchdog(poll_dir: str = "data/raw/watch/inbox", interval: int = 30) -> Any:
    global _WATCH_OBSERVER, _WATCH_POLL_THREAD, _WATCH_STOP_EVENT  # pyright: ignore[reportConstantRedefinition]
    # idempotent: if already running return existing observer
    if _WATCH_OBSERVER is not None:
        try:
            is_alive = getattr(_WATCH_OBSERVER, "is_alive", lambda: False)()
            if is_alive:
                return _WATCH_OBSERVER
        except Exception:
            pass
    watch_path = Path(poll_dir)
    watch_path.mkdir(parents=True, exist_ok=True)
    _load_seen()

    try:
        from watchdog.events import PatternMatchingEventHandler  # type: ignore[import-not-found]
        from watchdog.observers import Observer  # type: ignore[import-not-found]

        handler = PatternMatchingEventHandler(  # type: ignore[no-untyped-call]
            patterns=["*.csv", "*.json", "*.xml"],
            ignore_directories=True,
            case_sensitive=False,
        )

        def _on_created(event: Any) -> None:  # type: ignore[no-untyped-def]
            with contextlib.suppress(Exception):
                _handle_watch_file(str(event.src_path))

        def _on_modified(event: Any) -> None:  # type: ignore[no-untyped-def]
            with contextlib.suppress(Exception):
                _handle_watch_file(str(event.src_path))

        handler.on_created = _on_created  # type: ignore[method-assign,assignment]
        handler.on_modified = _on_modified  # type: ignore[method-assign,assignment]

        observer = Observer()  # type: ignore[no-untyped-call]
        observer.schedule(handler, str(watch_path), recursive=False)  # type: ignore[no-untyped-call]
        observer.start()  # type: ignore[no-untyped-call]
        _WATCH_OBSERVER = observer  # pyright: ignore[reportConstantRedefinition]

        # Poll thread fallback every interval seconds to catch missed events
        stop_ev = threading.Event()
        _WATCH_STOP_EVENT = stop_ev  # pyright: ignore[reportConstantRedefinition]

        def _poll_loop() -> None:
            while not stop_ev.is_set():
                try:
                    for ext in ("*.csv", "*.json", "*.xml"):
                        for fp in watch_path.glob(ext):
                            _handle_watch_file(str(fp))
                except Exception:
                    pass
                # wait with interruptible sleep
                stop_ev.wait(timeout=float(interval))

        t = threading.Thread(target=_poll_loop, daemon=True, name="watchdog-poll")
        t.start()
        _WATCH_POLL_THREAD = t  # pyright: ignore[reportConstantRedefinition]
        return observer
    except Exception:
        # fallback: polling thread only if watchdog not available
        stop_ev = threading.Event()
        _WATCH_STOP_EVENT = stop_ev  # pyright: ignore[reportConstantRedefinition]

        def _fallback_poll() -> None:
            while not stop_ev.is_set():
                try:
                    for ext in ("*.csv", "*.json", "*.xml"):
                        for fp in watch_path.glob(ext):
                            _handle_watch_file(str(fp))
                except Exception:
                    pass
                stop_ev.wait(timeout=float(interval))

        t = threading.Thread(target=_fallback_poll, daemon=True, name="watchdog-poll-fallback")
        t.start()
        _WATCH_POLL_THREAD = t  # pyright: ignore[reportConstantRedefinition]

        # create dummy observer-like object
        class _Dummy:
            def stop(self) -> None:
                stop_ev.set()

            def join(self, timeout: float | None = None) -> None:
                with contextlib.suppress(Exception):
                    t.join(timeout=timeout)

            def is_alive(self) -> bool:
                return t.is_alive()

        _WATCH_OBSERVER = _Dummy()  # pyright: ignore[reportConstantRedefinition]
        return _WATCH_OBSERVER


def stop_watchdog() -> None:  # pyright: ignore[reportConstantRedefinition]
    global _WATCH_OBSERVER, _WATCH_STOP_EVENT  # pyright: ignore[reportConstantRedefinition]
    try:
        if _WATCH_STOP_EVENT is not None:
            _WATCH_STOP_EVENT.set()
    except Exception:
        pass
    try:
        if _WATCH_OBSERVER is not None:
            stop_fn = getattr(_WATCH_OBSERVER, "stop", None)
            if callable(stop_fn):
                stop_fn()
            join_fn = getattr(_WATCH_OBSERVER, "join", None)
            if callable(join_fn):
                with contextlib.suppress(Exception):
                    join_fn(timeout=2)
    except Exception:
        pass
    _WATCH_OBSERVER = None  # pyright: ignore[reportConstantRedefinition]
    _WATCH_STOP_EVENT = None  # pyright: ignore[reportConstantRedefinition]


def _ingest_and_store(src: str, filename: str, engine: str) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    out_parquet = _PARQUET_DIR / f"{job_id}_{Path(filename).stem}.parquet"
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    result = ingest_file(src, str(out_parquet), str(_VALIDATION_JSON), engine=engine)
    _normalize_parquet(out_parquet)
    entry: dict[str, Any] = {
        "id": job_id,
        "job_id": job_id,
        "filename": filename,
        "status": "done",
        "rows_ok": result.get("rows_ok", 0),
        "rows_quarantined": result.get("rows_quarantined", 0),
        "parquet": str(out_parquet),
    }
    INGEST_JOBS[job_id] = {
        "id": job_id,
        "status": "done",
        "rows_ok": entry["rows_ok"],
        "rows_quarantined": entry["rows_quarantined"],
        "quarantined": entry["rows_quarantined"],
        "parquet": str(out_parquet),
        "filename": filename,
    }
    return entry


@router.post("/ingest/watch/start")
def watch_start(poll_dir: str = "data/raw/watch/inbox", interval: int = 30) -> dict[str, Any]:
    obs = start_watchdog(poll_dir=poll_dir, interval=interval)
    alive = False
    try:
        alive = bool(getattr(obs, "is_alive", lambda: True)())
    except Exception:
        alive = True
    return {"status": "started", "poll_dir": poll_dir, "interval": interval, "alive": alive}


@router.get("/ingest/watch/status")
def watch_status() -> dict[str, Any]:
    _load_seen()
    # count unique watched files (filter to real path keys not hash keys)
    count = 0
    try:
        # seen_hashes contains both path->hash and hash->hash; count path entries that exist as keys
        for k, v in _seen_hashes.items():
            # path keys contain '/' and not ':' hash? hash keys contain ':' + mtime
            # hash keys have ':' and numeric mtime; path keys are absolute paths starting with /
            if k == v and ":" in k:
                continue
            if ":" in str(v) and k != v:
                count += 1
        # fallback: if no path entries, count distinct hash values
        if count == 0 and _seen_hashes:
            # distinct hash values
            count = len(set(_seen_hashes.values()))
    except Exception:
        count = len(_seen_hashes)
    alive = False
    try:
        if _WATCH_OBSERVER is not None:
            alive = bool(getattr(_WATCH_OBSERVER, "is_alive", lambda: False)())
    except Exception:
        alive = False
    return {
        "watched_files_count": count,
        "seen_count": count,
        "alive": alive,
        "poll_dir": str(_WATCH_DIR_DEFAULT),
    }


@router.post("/ingest")
async def ingest_multipart(file: UploadFile = File(...)) -> dict[str, Any]:  # type: ignore[no-untyped-def]  # noqa: B008
    if file.filename is None or file.filename.strip() == "":
        raise HTTPException(status_code=422, detail="filename required")
    filename = file.filename
    job_id = str(uuid.uuid4())
    tmp_path = _TMP_DIR / f"{job_id}_{Path(filename).name}"
    data = await file.read()
    tmp_path.write_bytes(data)
    try:
        _ = detect_format(str(tmp_path))
        engine = _get_engine()
        out_parquet = _PARQUET_DIR / f"{job_id}_{Path(filename).stem}.parquet"
        out_parquet.parent.mkdir(parents=True, exist_ok=True)
        result = ingest_file(str(tmp_path), str(out_parquet), str(_VALIDATION_JSON), engine=engine)
        _normalize_parquet(out_parquet)
        resp: dict[str, Any] = {
            "id": job_id,
            "job_id": job_id,
            "filename": filename,
            "status": "done",
            "rows_ok": result.get("rows_ok", 0),
            "rows_quarantined": result.get("rows_quarantined", 0),
            "parquet": str(out_parquet),
            "validation_report": str(_VALIDATION_JSON),
            "engine": engine,
        }
        INGEST_JOBS[job_id] = {
            "id": job_id,
            "status": "done",
            "rows_ok": resp["rows_ok"],
            "rows_quarantined": resp["rows_quarantined"],
            "quarantined": resp["rows_quarantined"],
            "parquet": str(out_parquet),
            "filename": filename,
        }
        return resp
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


@router.post("/ingest/batch")
async def ingest_batch(
    folder: str | None = Form(default=None),
    files: list[UploadFile] | None = File(default=None),  # noqa: B008
) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    engine = _get_engine()
    jobs: list[dict[str, Any]] = []
    if folder is not None and folder.strip() != "":
        p = Path(folder.strip())
        if not p.exists() or not p.is_dir():
            raise HTTPException(status_code=422, detail=f"folder not found: {folder}")
        cands = sorted([*p.glob("*.csv"), *p.glob("*.json"), *p.glob("*.xml")])
        if not cands:
            return {"jobs": [], "count": 0, "engine": engine}
        for fp in cands:
            jobs.append(_ingest_and_store(str(fp), fp.name, engine))
        return {"jobs": jobs, "count": len(jobs), "engine": engine}
    if files:
        for f in files:
            if f.filename is None:
                continue
            tmp_path = _TMP_DIR / f"{uuid.uuid4()}_{Path(f.filename).name}"
            tmp_path.write_bytes(await f.read())
            try:
                jobs.append(_ingest_and_store(str(tmp_path), f.filename, engine))
            finally:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except Exception:
                    pass
        return {"jobs": jobs, "count": len(jobs), "engine": engine}
    raise HTTPException(status_code=422, detail="provide folder or files")


@router.get("/ingest/status/{job_id}")
def ingest_status(job_id: str) -> dict[str, Any]:
    job = INGEST_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "id": job_id,
        "status": job.get("status", "done"),
        "rows_ok": job.get("rows_ok", 0),
        "quarantined": job.get("quarantined", job.get("rows_quarantined", 0)),
        "rows_quarantined": job.get("rows_quarantined", job.get("quarantined", 0)),
        "parquet": job.get("parquet", ""),
        "filename": job.get("filename", ""),
    }


@router.get("/validation/{file}")
def validation_report(file: str) -> list[dict[str, Any]]:
    if not _VALIDATION_JSON.exists():
        return []
    try:
        text = _VALIDATION_JSON.read_text(encoding="utf-8").strip()
        if not text:
            return []
        data = json.loads(text)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        f = str(entry.get("file", ""))
        if (
            f == file
            or f.endswith("/" + file)
            or f.endswith(file)
            or file in f
            or Path(f).name == file
        ):
            out.append(entry)
    return out


def _mock_mempool_payload(height: int = 2) -> dict[str, Any]:
    # same shape as GET /api/mock/mempool; height param allows increment
    base_h = height - 1 if height >= 2 else 1
    return {
        "blocks": [
            {
                "height": base_h,
                "hash": "0" * 64,
                "tx_count": 1,
                "timestamp": 1700000000 + (base_h - 1) * 600,
            },
            {
                "height": height,
                "hash": "1" * 64,
                "tx_count": 2,
                "timestamp": 1700000600 + (height - 2) * 600,
            },
        ],
        "mempool-blocks": [
            {"blockVSize": 1, "nTx": 1, "totalFees": 1000, "medianFee": 5},
            {"blockVSize": 2, "nTx": 2, "totalFees": 2000, "medianFee": 6},
        ],
    }


@router.get("/mock/mempool")
def mock_mempool() -> dict[str, Any]:
    return _mock_mempool_payload(height=2)


@router.websocket("/ws/mock/mempool")
async def ws_mock_mempool(websocket: WebSocket) -> None:
    await websocket.accept()
    height = 2
    try:
        while True:
            payload = _mock_mempool_payload(height=height)
            await websocket.send_json(payload)
            height += 1
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close()
        return


@ws_router.websocket("/ws/mock/mempool")
async def ws_mock_mempool_root(websocket: WebSocket) -> None:
    await websocket.accept()
    height = 2
    try:
        while True:
            payload = _mock_mempool_payload(height=height)
            await websocket.send_json(payload)
            height += 1
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close()
        return


@router.get("/replay")
def replay(at: str = Query(...)) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    # tightened: at required, 422 if missing/invalid handled via _parse_at + FastAPI Query(...)
    dt = _parse_at(at)
    if dt is None:
        raise HTTPException(status_code=422, detail="at query param required (ISO8601)")
    parquet_files = sorted(
        _PARQUET_DIR.glob("*.parquet"), key=lambda p: p.stat().st_mtime if p.exists() else 0
    )
    if not parquet_files:
        if (_PARQUET_DIR / "demo.parquet").exists():
            parquet_files = [_PARQUET_DIR / "demo.parquet"]
        else:
            return {"rows": [], "count": 0, "at": at}
    import polars as pl  # type: ignore[import-not-found]

    frames: list[pl.DataFrame] = []
    for pf in parquet_files:
        try:
            df = pl.read_parquet(str(pf))
            if df.height > 0:
                frames.append(df)
        except Exception:
            continue
    if not frames:
        return {"rows": [], "count": 0, "at": at}
    try:
        combined = pl.concat(frames, how="vertical_relaxed")  # type: ignore[arg-type]
    except Exception:
        combined = frames[0]
    # limit 1000 applied after filtering
    limit = 1000
    if "timestamp" in combined.columns:
        try:
            # Use duckdb or polars branching: try polars first
            if combined["timestamp"].dtype == pl.Utf8:  # type: ignore[attr-defined]
                combined = combined.with_columns(pl.col("timestamp").str.to_datetime(strict=False))
            # Ensure dt is timezone-aware matching column
            # polars datetime may be tz-aware; filter via python dt compare
            filtered = combined.filter(pl.col("timestamp") <= dt)
            # apply limit
            if filtered.height > limit:
                filtered = filtered.head(limit)
            rows = filtered.to_dicts()  # type: ignore[no-untyped-call]
            return {"rows": rows, "count": len(rows), "at": at}
        except HTTPException:
            raise
        except Exception:
            # fallback: try duckdb read via polars to_dicts then manual filter
            try:
                all_rows: list[dict[str, Any]] = combined.to_dicts()  # type: ignore[no-untyped-call]
                # manual dt compare if timestamp is datetime
                filtered_rows: list[dict[str, Any]] = []
                for r in all_rows:
                    ts = r.get("timestamp")
                    try:
                        if isinstance(ts, str):
                            s = ts.strip()
                            if s.endswith("Z"):
                                s = s[:-1] + "+00:00"
                            ts_dt = datetime.fromisoformat(s)
                            if ts_dt.tzinfo is None:
                                ts_dt = ts_dt.replace(tzinfo=UTC)
                        elif isinstance(ts, datetime):
                            ts_dt = ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)
                        else:
                            continue
                        if ts_dt <= dt:
                            filtered_rows.append(r)
                            if len(filtered_rows) >= limit:
                                break
                    except Exception:
                        continue
                return {
                    "rows": filtered_rows[:limit],
                    "count": len(filtered_rows[:limit]),
                    "at": at,
                }
            except Exception:
                rows2 = combined.to_dicts()  # type: ignore[no-untyped-call]
                return {"rows": rows2[:limit], "count": min(len(rows2), limit), "at": at}
    rows_all = combined.to_dicts()  # type: ignore[no-untyped-call]
    # if no timestamp filter possible, just limit
    return {"rows": rows_all[:limit], "count": min(len(rows_all), limit), "at": at}
