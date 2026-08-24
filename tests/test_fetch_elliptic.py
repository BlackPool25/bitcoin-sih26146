"""Tests for scripts/fetch_elliptic.py offline-safe fetch+verify."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPT = Path("scripts/fetch_elliptic.py")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_files(out: Path, contents: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        (out / name).write_bytes(data)


def _write_sums(out: Path, hashes: dict[str, str]) -> None:
    lines = [f"{h}  {name}" for name, h in hashes.items()]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_offline_warn_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "elliptic"
    out.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in __import__("os").environ.items() if k != "KAGGLE_USERNAME"}
    # also ensure unset explicitly
    env.pop("KAGGLE_USERNAME", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--verify"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, f"exit code {result.returncode} stderr {result.stderr}"
    # must warn fallback, not crash
    assert "WARN" in result.stderr
    assert "elliptic missing" in result.stderr.lower() or "fallback faker" in result.stderr.lower()


def test_idempotent_skip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # create real files matching SHA256SUMS placeholder (empty files)
    sys.path.insert(0, "scripts")
    try:
        import fetch_elliptic as fe  # type: ignore[import-not-found]
        import importlib

        importlib.reload(fe)
        out = tmp_path / "elliptic2"
        out.mkdir(parents=True, exist_ok=True)
        # empty files match EMPTY_SHA256 already in SHA256SUMS
        for fname in fe.EXPECTED_FILES:
            (out / fname).write_bytes(b"")
        # copy real SHA256SUMS from repo data
        src_sums = Path("data/raw/elliptic/SHA256SUMS")
        if src_sums.is_file():
            (out / "SHA256SUMS").write_text(src_sums.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            hashes = {f: fe.EMPTY_SHA256 for f in fe.EXPECTED_FILES}
            _write_sums(out, hashes)
        # first verify_all should pass
        assert fe.verify_all(out) is True
        # second call with --force false should hit cache path: simulate main cache check
        # patch fetch methods to ensure they are NOT called
        with mock.patch.object(fe, "try_kaggle") as mk, mock.patch.object(
            fe, "try_curl_mirrors"
        ) as mc, mock.patch.object(fe, "try_bundle") as mb:
            # mimic main's idempotent check
            assert fe.all_exist(out) is True
            assert fe.verify_all(out) is True
            # if we were in main, we would exit 0 without calling fetch
            mk.assert_not_called()
            mc.assert_not_called()
            mb.assert_not_called()
        # also test via subprocess second run hits cache log
        env = {k: v for k, v in __import__("os").environ.items()}
        env.pop("KAGGLE_USERNAME", None)
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--out", str(out), "--verify"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert r.returncode == 0
        assert "cache" in r.stderr.lower() or "skipping download" in r.stderr.lower() or "OK verify" in r.stderr
    finally:
        if "scripts" in sys.path:
            sys.path.remove("scripts")


def test_verify_success_and_fail(tmp_path: Path) -> None:
    sys.path.insert(0, "scripts")
    try:
        import fetch_elliptic as fe  # type: ignore[import-not-found]
        import importlib

        importlib.reload(fe)
        out = tmp_path / "elliptic3"
        out.mkdir(parents=True, exist_ok=True)
        data = b"hello elliptic"
        h = _sha256_bytes(data)
        # success case: write file and matching sums
        _write_files(out, {fe.EXPECTED_FILES[0]: data})
        # fill other expected files with same data for simplicity
        for fname in fe.EXPECTED_FILES[1:]:
            (out / fname).write_bytes(data)
        hashes = {f: h for f in fe.EXPECTED_FILES}
        _write_sums(out, hashes)
        assert fe.verify_all(out) is True
        # single file verify_one success
        assert fe.verify_one(out / fe.EXPECTED_FILES[0], h) is True
        # fail case: tamper one file
        (out / fe.EXPECTED_FILES[1]).write_bytes(b"tampered")
        assert fe.verify_all(out) is False
        # verify_one direct fail
        assert fe.verify_one(out / fe.EXPECTED_FILES[1], h) is False
        # missing file fail
        (out / fe.EXPECTED_FILES[2]).unlink()
        assert fe.verify_all(out) is False
    finally:
        if "scripts" in sys.path:
            sys.path.remove("scripts")


def test_mock_network_no_crash(tmp_path: Path) -> None:
    sys.path.insert(0, "scripts")
    try:
        import fetch_elliptic as fe  # type: ignore[import-not-found]
        import importlib

        importlib.reload(fe)
        out = tmp_path / "elliptic4"
        out.mkdir(parents=True, exist_ok=True)
        # mock network to raise URLError, mock kaggle to fail
        with mock.patch("urllib.request.urlopen", side_effect=__import__("urllib").error.URLError("offline")):
            with mock.patch("subprocess.run", return_value=mock.MagicMock(returncode=1, stderr="nope")):
                # with no env kaggle, try_kaggle should skip
                with mock.patch.dict("os.environ", {}, clear=False):
                    if "KAGGLE_USERNAME" in __import__("os").environ:
                        del __import__("os").environ["KAGGLE_USERNAME"]
                    assert fe.try_kaggle(out) is False
                    assert fe.try_curl_mirrors(out) is False
                    assert fe.try_bundle(out) is False
                    # all_exist false -> verify fails but not crash
                    assert fe.all_exist(out) is False
                    assert fe.verify_all(out) is False
    finally:
        if "scripts" in sys.path:
            sys.path.remove("scripts")
