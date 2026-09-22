"""FastAPI emitter — complete runnable backend from an IR."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..core import IR, camel, pascal, plural, sample_payload
from ._shared import GITIGNORE, py_reqs, py_schemas, py_store, readme


def emit(ir: IR, project: str, opts: Optional[Dict[str, Any]] = None) -> tuple[List[Dict[str, str]], List[str]]:
    opts = opts or {}
    auth = bool(opts.get("auth", True))
    health = bool(opts.get("health", True))
    files: List[Dict[str, str]] = []
    notes: List[str] = [
        f"{len(ir.models)} model(s), {len(ir.enums)} enum(s) parsed deterministically.",
        "In-memory store + deterministic seed — runnable with zero external services.",
        "Swap app/store.py for a real DB when ready (SQLAlchemy/Alembic are already in the stack).",
    ]

    def add(path: str, rendered: str) -> None:
        files.append({"output": path, "rendered": rendered})

    add(".gitignore", GITIGNORE)
    add("README.md", readme(project, "fastapi", json.dumps(opts.get("goal", ""))[:300]))
    add("requirements.txt", py_reqs(["fastapi>=0.111", "uvicorn>=0.30", "pytest>=8", "httpx>=0.27"]))
    add("pyproject.toml", '[tool.pytest.ini_options]\npythonpath = ["."]\ntestpaths = ["tests"]\n')
    add("app/__init__.py", "")
    add("app/schemas.py", py_schemas(ir))
    add("app/store.py", py_store(ir))
    add("app/routes.py", _routes_py(ir, auth))
    add("app/main.py", _main_py(ir, auth, health))
    if auth:
        add("app/security.py", _security_py())
    add("tests/test_api.py", _test_py(ir, auth, health))
    return files, notes


def _security_py() -> str:
    return (
        "import os\n"
        "from fastapi import Header, HTTPException\n\n"
        "def require_token(authorization: str | None = Header(default=None)) -> None:\n"
        "    token = os.environ.get('API_TOKEN', '')\n"
        "    if not token:\n"
        "        raise HTTPException(status_code=503, detail='API_TOKEN not configured')\n"
        "    expected = f'Bearer {token}'\n"
        "    if authorization != expected:\n"
        "        raise HTTPException(status_code=401, detail='invalid token')\n"
    )


def _routes_py(ir: IR, auth: bool) -> str:
    dep_import = "from fastapi import APIRouter, Depends, HTTPException\n"
    lines = [
        "from fastapi import APIRouter, HTTPException",
        "from . import schemas",
        "from .store import list_rows, get_row, create_row, update_row, delete_row",
    ]
    if auth:
        lines.append("from .security import require_token")
        dep = "Depends(require_token), "
    else:
        dep = ""
    lines += ["", "api = APIRouter()", "", "def _payload(row):", "    return {k: v for k, v in row.items()}", ""]
    for model in ir.models:
        c = pascal(model.name)
        lname = camel(model.name)
        path = f"/{plural(lname)}"
        mid = f"{lname}_id"
        dynamic = path + "/{" + mid + "}"
        lines.append(f"@api.get({json.dumps(path)})")
        lines.append(f"def list_{lname}() -> list[schemas.{c}]:")
        lines.append(f"    return [_payload(r) for r in list_rows({json.dumps(lname)})]")
        lines.append("")
        lines.append(f"@api.post({json.dumps(path)}, status_code=201)")
        lines.append(f"def create_{lname}(payload: schemas.{c}Create) -> schemas.{c}:")
        lines.append(f"    return create_row({json.dumps(lname)}, payload.model_dump())")
        lines.append("")
        lines.append(f"@api.get({json.dumps(dynamic)})")
        lines.append(f"def get_{lname}({mid}: str) -> schemas.{c}:")
        lines.append(f"    row = get_row({json.dumps(lname)}, {mid})")
        lines.append("    if row is None:")
        lines.append("        raise HTTPException(status_code=404, detail='not found')")
        lines.append("    return _payload(row)")
        lines.append("")
        lines.append(f"@api.put({json.dumps(dynamic)})")
        lines.append(f"def update_{lname}({mid}: str, payload: schemas.{c}Update) -> schemas.{c}:")
        lines.append(f"    row = update_row({json.dumps(lname)}, {mid}, payload.model_dump(exclude_none=True))")
        lines.append("    if row is None:")
        lines.append("        raise HTTPException(status_code=404, detail='not found')")
        lines.append("    return _payload(row)")
        lines.append("")
        lines.append(f"@api.delete({json.dumps(dynamic)}, status_code=204)")
        lines.append(f"def delete_{lname}({mid}: str) -> None:")
        lines.append(f"    if not delete_row({json.dumps(lname)}, {mid}):")
        lines.append("        raise HTTPException(status_code=404, detail='not found')")
        lines.append("")
    return "\n".join(lines)


def _main_py(ir: IR, auth: bool, health: bool) -> str:
    lines = [
        "from fastapi import FastAPI",
        "from .routes import api",
        "",
        "app = FastAPI()",
        "app.include_router(api)",
        "",
    ]
    if health:
        lines += [
            "@app.get('/health')",
            "def health():",
            "    return {'status': 'ok'}",
            "",
        ]
    return "\n".join(lines)


def _test_py(ir: IR, auth: bool, health: bool) -> str:
    headers = "{'Authorization': 'Bearer test-token'}" if auth else "{}"
    lines = [
        "import os",
        "from fastapi.testclient import TestClient",
        "from app.main import app",
        "from app.store import seed",
        "",
        "os.environ['API_TOKEN'] = 'test-token'",
        "client = TestClient(app)",
        "",
        "def setup_function():\n    seed()\n",
        "def _h():\n    return " + headers + "\n",
    ]
    if health:
        lines += ["def test_health():\n    assert client.get('/health').status_code == 200\n"]
    for model in ir.models:
        c = pascal(model.name)
        lname = camel(model.name)
        path = f"/{plural(lname)}"
        payload = "{}" if not sample_payload(model, ir.enums, "py") else "{" + ", ".join(sample_payload(model, ir.enums, "py")) + "}"
        lines.append(f"def test_{lname}_crud():")
        lines.append(f"    created = client.post({json.dumps(path)}, json={payload}, headers=_h())")
        lines.append("    assert created.status_code == 201")
        lines.append("    row = created.json()")
        lines.append("    assert row['id']")
        lines.append(f"    assert client.get({json.dumps(path)}).status_code == 200")
        lines.append(f"    assert client.get({json.dumps(path + '/' + lname + '_1')}).status_code == 200")
        lines.append(f"    assert client.get({json.dumps(path + '/missing')}).status_code == 404")
        lines.append(f"    assert client.put({json.dumps(path + '/' + lname + '_1')}, json={{}}, headers=_h()).status_code == 200")
        lines.append(f"    assert client.delete({json.dumps(path + '/' + lname + '_1')}, headers=_h()).status_code == 204")
        lines.append("")
    return "\n".join(lines)