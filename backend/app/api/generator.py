"""BigBack deterministic generator API routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from generator import generate, materialize
from generator.frameworks import available

generator_router = APIRouter(prefix="/generator", tags=["generator"])


class SpecRequest(BaseModel):
    project: Optional[str] = None
    framework: Optional[str] = None
    auth: Optional[bool] = None
    database: Optional[str] = None
    cache: Optional[str] = None
    health: Optional[bool] = None
    schema_text: Optional[str] = None
    goal: Optional[str] = None


class MaterializeRequest(SpecRequest):
    target_dir: str = "out"


@generator_router.get("/frameworks")
def list_frameworks() -> Dict[str, Any]:
    """List the deterministic backend frameworks the generator can emit."""
    return {"ok": True, "frameworks": list(available())}


@generator_router.post("/plan")
def plan(req: SpecRequest) -> Dict[str, Any]:
    """Generate a backend file plan in-memory (no writes). Returns files[].rendered."""
    body = req.model_dump(exclude_none=True)
    if "schema_text" in body:
        body["schema"] = body.pop("schema_text")
    return generate(body)


@generator_router.post("/materialize")
def do_materialize(req: MaterializeRequest) -> Dict[str, Any]:
    """Generate and write the backend to target_dir (confined to a base dir)."""
    base = Path(os.environ.get("BIGBACK_OUT_ROOT", ".")).resolve()
    target = (base / req.target_dir.lstrip("/\\")).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_dir escapes BIGBACK_OUT_ROOT")
    spec = req.model_dump(exclude_none=True)
    spec.pop("target_dir", None)
    if "schema_text" in spec:
        spec["schema"] = spec.pop("schema_text")
    result = materialize(str(target), spec)
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error", "generation failed"))
    return result