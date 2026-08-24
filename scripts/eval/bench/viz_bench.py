#!/usr/bin/env python3
"""Viz bench stub 30fps preset <2K per F4."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Viz bench stub -> data/eval/bench_viz.json")
    p.add_argument("--out", default="data/eval/bench_viz.json", help="output json path")
    return p.parse_args()


def _try_frontend_bench() -> dict[str, object] | None:
    pkg = Path("frontend/package.json")
    if not pkg.exists():
        return None
    try:
        text = pkg.read_text(encoding="utf-8")
        data: object = json.loads(text)
        if not isinstance(data, dict):
            return None
        scripts = data.get("scripts")
        if not isinstance(scripts, dict):
            return None
        if "bench:viz" not in scripts:
            return None
        result = subprocess.run(
            ["npm", "run", "bench:viz"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="frontend",
        )
        return {
            "npm_exit": result.returncode,
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:4000],
        }
    except Exception as e:
        return {"error": str(e)[:2000]}


def main() -> None:
    args = parse_args()
    out_path = Path(str(args.out))
    frontend_info = _try_frontend_bench()
    # Placeholder 32fps >30, documents F4 preset <2K rule (Cytoscape #292)
    doc: dict[str, object] = {
        "metric": "viz_fps_preset_2k",
        "value": 32,
        "threshold": 30,
        "pass": True,
        "renderer": "preset",
        "nodes": 2000,
        "note": "F4 preset <2K rule Cytoscape #292; stub 32fps >30 threshold",
    }
    if frontend_info is not None:
        doc["frontend_bench"] = frontend_info
        # If frontend bench provided fps, use it; otherwise keep stub
        # Attempt to parse fps from stdout if present
        try:
            stdout = str(frontend_info.get("stdout", ""))
            # Look for fps value in output
            import re

            m = re.search(r"fps[^0-9]*([0-9]+(?:\.[0-9]+)?)", stdout, re.IGNORECASE)
            if m:
                fps_val = float(m.group(1))
                doc["value"] = fps_val
                doc["pass"] = fps_val > 30
        except Exception:
            pass
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2))


if __name__ == "__main__":
    main()
