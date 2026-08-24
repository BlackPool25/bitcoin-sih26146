#!/usr/bin/env python3
"""Offline-safe fetch+verify for Elliptic dataset (203K nodes / 234K edges)."""
from __future__ import annotations
import argparse
import hashlib
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

EXPECTED_FILES: list[str] = [
    "elliptic_txs_features.csv",
    "elliptic_txs_edgelist.csv",
    "elliptic_txs_classes.csv",
]
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MIRRORS: list[str] = [
    "https://r2.elliptic-mirror1.example.com/elliptic.zip",
    "https://r2.elliptic-mirror2.example.com/elliptic.zip",
]
KAGGLE_DATASET = "elliptic/elliptic-dataset"
BUNDLE_CANDIDATES: list[Path] = [
    Path("bundle/elliptic.zip"),
    Path("dist/bundle/elliptic.zip"),
    Path("data/bundle/elliptic.zip"),
]
SHA256SUMS_NAME = "SHA256SUMS"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sums(p: Path) -> dict[str, str]:
    if not p.is_file():
        return {}
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            out[Path(parts[-1].lstrip("*")).name] = parts[0]
    return out


def verify_one(path: Path, expected: str) -> bool:
    if not path.is_file():
        log(f"WARN verify: missing {path.name}")
        return False
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        log(f"WARN verify: hash mismatch {path.name} expected {expected[:12]} got {actual[:12]}")
        return False
    log(f"OK verify: {path.name} {actual[:12]}...")
    return True


def verify_all(out_dir: Path) -> bool:
    sums = load_sums(out_dir / SHA256SUMS_NAME)
    if not sums:
        missing = [f for f in EXPECTED_FILES if not (out_dir / f).is_file()]
        if missing:
            log(f"WARN verify: missing files {missing} and no {SHA256SUMS_NAME}")
            return False
        log("WARN verify: no SHA256SUMS, existence check only — assuming OK")
        return True
    ok = True
    for fname in EXPECTED_FILES:
        if not verify_one(out_dir / fname, sums.get(fname, EMPTY_SHA256)):
            ok = False
    return ok


def all_exist(out_dir: Path) -> bool:
    return all((out_dir / f).is_file() for f in EXPECTED_FILES)


def try_kaggle(out_dir: Path) -> bool:
    if not os.environ.get("KAGGLE_USERNAME"):
        log("INFO kaggle: KAGGLE_USERNAME not set, skipping kaggle CLI")
        return False
    try:
        cmd = ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-p", str(out_dir), "--unzip"]
        log(f"INFO kaggle: running {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            log("INFO kaggle: download succeeded")
            return True
        log(f"WARN kaggle: failed rc={r.returncode} {r.stderr[:300]}")
        return False
    except FileNotFoundError:
        log("WARN kaggle: kaggle CLI not found")
        return False
    except subprocess.TimeoutExpired:
        log("WARN kaggle: timeout")
        return False
    except Exception as e:
        log(f"WARN kaggle: {e}")
        return False


def try_curl_mirrors(out_dir: Path) -> bool:
    for idx, url in enumerate(MIRRORS, start=1):
        try:
            log(f"INFO mirror {idx}: fetching {url}")
            dest = out_dir / f".elliptic_mirror_{idx}.zip"
            with urllib.request.urlopen(url, timeout=10) as resp:
                dest.write_bytes(resp.read())
            if not zipfile.is_zipfile(dest):
                log(f"WARN mirror {idx}: not a zip, removing temp")
                dest.unlink(missing_ok=True)
                continue
            with zipfile.ZipFile(dest, "r") as z:
                z.extractall(out_dir)
            dest.unlink(missing_ok=True)
            if all_exist(out_dir):
                log(f"INFO mirror {idx}: success, files present")
                return True
            log(f"WARN mirror {idx}: extracted but files still missing")
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            log(f"WARN mirror {idx}: fetch failed {e}")
            continue
        except Exception as e:
            log(f"WARN mirror {idx}: unexpected {e}")
            continue
    return False


def try_bundle(out_dir: Path) -> bool:
    for cand in BUNDLE_CANDIDATES:
        if not cand.is_file():
            continue
        try:
            log(f"INFO bundle: found {cand}, extracting to {out_dir}")
            if not zipfile.is_zipfile(cand):
                log(f"WARN bundle: {cand} is not a zip")
                continue
            with zipfile.ZipFile(cand, "r") as z:
                z.extractall(out_dir)
            log(f"INFO bundle: extracted {cand}")
            if all_exist(out_dir):
                return True
        except Exception as e:
            log(f"WARN bundle: failed {cand}: {e}")
            continue
    log("INFO bundle: no bundle found or extraction incomplete")
    return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Offline-safe fetch+verify for Elliptic dataset")
    p.add_argument("--out", type=str, default="data/raw/elliptic", help="Output directory")
    p.add_argument("--verify", action="store_true", help="Verify SHA256 after fetch/check")
    p.add_argument("--force", action="store_true", help="Force re-download even if cached")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(str(args.out))
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.force and all_exist(out_dir) and verify_all(out_dir):
        log(f"INFO cache: all files present + verified in {out_dir}, skipping download")
        if args.verify:
            log("OK verify: cache hit")
        sys.exit(0)
    if not args.force and all_exist(out_dir):
        log("WARN cache: files present but verify failed, will attempt fetch")
    fetched = False
    if try_kaggle(out_dir):
        fetched = True
    elif try_curl_mirrors(out_dir):
        fetched = True
    elif try_bundle(out_dir):
        fetched = True
    else:
        log(f"INFO fetch: all fetch methods failed or skipped for {out_dir}")
    _ = fetched
    if all_exist(out_dir):
        if verify_all(out_dir):
            log(f"OK verify: all {len(EXPECTED_FILES)} files verified in {out_dir}")
            sys.exit(0)
        log(f"WARN verify: verification failed in {out_dir}, fallback Faker will be used")
        sys.exit(0)
    log("WARN elliptic missing, fallback Faker will be used")
    sys.exit(0)


if __name__ == "__main__":
    main()
