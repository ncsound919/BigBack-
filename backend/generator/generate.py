"""BigBack generator orchestrator.

`generate(spec)` deterministically produces a complete runnable backend for the
requested framework from an entity DSL schema. Zero LLM, zero network. The same
spec always produces the same bytes (including a manifest for drift checks).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .core import IR, parse_schema, spec_defaults
from .frameworks import available, emit_for

VERSION = "2.1.0-generator"

KNOWN_KEYS = {"project", "framework", "auth", "database", "cache", "health", "schema", "goal"}


def normalize_spec(spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = dict(spec_defaults())
    if spec and isinstance(spec, dict):
        for k in KNOWN_KEYS:
            if k in spec:
                merged[k] = spec[k]
    raw = str(merged.get("project") or "my-service")
    merged["project"] = re.sub(r"[^a-z0-9 _-]", "", raw.lower()).replace(" ", "-")[:40] or "my-service"
    if merged.get("framework") not in available():
        merged["framework"] = "fastapi"
    return merged


def generate(spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = normalize_spec(spec)
    framework = cfg["framework"]
    project = cfg["project"]

    try:
        ir: IR = parse_schema(str(cfg.get("schema") or ""))
    except ValueError as exc:
        return {"ok": False, "error": f"schema parse failed: {exc}", "framework": framework}

    files: List[Dict[str, str]] = []
    manifest: List[str] = []

    def add(path: str, rendered: str) -> None:
        files.append({"output": path, "rendered": rendered})
        manifest.append(path)

    emitted, notes = emit_for(framework, ir, project, cfg)
    for f in emitted:
        add(f["output"], f["rendered"])

    add("bigback.spec.json", json.dumps({k: cfg[k] for k in KNOWN_KEYS if k in cfg}, indent=2) + "\n")
    manifest_rendered = json.dumps({
        "engine": VERSION,
        "framework": framework,
        "project": project,
        "generated": manifest,
    }, indent=2) + "\n"
    files.append({"output": "bigback.manifest.json", "rendered": manifest_rendered})

    return {
        "ok": True,
        "framework": framework,
        "project": project,
        "models": [m.name for m in ir.models],
        "enums": list(ir.enums.keys()),
        "files": files,
        "manifest": manifest,
        "notes": notes,
        "available_frameworks": list(available()),
    }


def materialize(root: str, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate and write the backend to disk (root-confined)."""
    from pathlib import Path

    plan = generate(spec)
    if not plan.get("ok"):
        return plan
    base = Path(root).resolve()
    written: List[str] = []
    for f in plan["files"]:
        rel = str(f["output"]).lstrip("/\\")
        if not rel or ".." in rel:
            continue
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f["rendered"], encoding="utf-8")
        written.append(rel)
    return {**plan, "written": written, "root": str(base)}