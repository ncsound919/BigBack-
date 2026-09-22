"""Flask (Python) emitter — complete runnable backend from an IR."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..core import IR, camel, pascal, plural, sample_payload, py_type
from ._shared import GITIGNORE, py_reqs, py_store, readme


def emit(ir: IR, project: str, opts: Optional[Dict[str, Any]] = None) -> tuple[List[Dict[str, str]], List[str]]:
    opts = opts or {}
    auth = bool(opts.get("auth", True))
    health = bool(opts.get("health", True))
    files: List[Dict[str, str]] = []
    notes: List[str] = [
        f"{len(ir.models)} model(s), {len(ir.enums)} enum(s) parsed deterministically.",
        "Flask is minimal — validation is a small deterministic helper, not a framework.",
    ]

    def add(path: str, rendered: str) -> None:
        files.append({"output": path, "rendered": rendered})

    add(".gitignore", GITIGNORE)
    add("README.md", readme(project, "flask", json.dumps(opts.get("goal", ""))[:300]))
    add("requirements.txt", py_reqs(["flask>=3.0", "pytest>=8"]))
    add("app/__init__.py", _factory_py(ir, auth, health))
    add("app/store.py", py_store(ir))
    add("app/validate.py", _validate_py(ir))
    add("app/routes.py", _routes_py(ir, auth))
    add("app/main.py", "from app import create_app\n\napp = create_app()\n")
    add("tests/test_api.py", _test_py(ir, auth, health))
    return files, notes


def _validate_py(ir: IR) -> str:
    lines = [
        '"""Deterministic field validation for generated Flask APIs."""',
        "from typing import Any",
        "",
        "_VALIDATORS = {}",
        "",
    ]
    for model in ir.models:
        c = pascal(model.name)
        lines.append(f"def _check_{c.lower()}(payload: dict[str, Any]) -> list[str]:")
        lines.append("    errors: list[str] = []")
        for f in model.fields:
            if f.pk:
                continue
            name = f.name
            optional = f.optional or f.list
            if f.type in ir.enums:
                allowed = ir.enums[f.type]
                lines.append(f"    if {name!r} in payload and payload[{name!r}] not in {allowed!r}:")
                lines.append(f"        errors.append({name!r} + ' must be one of ' + {str(allowed)!r})")
            elif f.type == "int":
                lines.append(f"    if {name!r} in payload and payload[{name!r}] is not None and not isinstance(payload[{name!r}], int):")
                lines.append(f"        errors.append({name!r} + ' must be an int')")
            elif f.type in ("float", "bool"):
                lines.append(f"    if {name!r} in payload and payload[{name!r}] is not None and not isinstance(payload[{name!r}], {f.type}):")
                lines.append(f"        errors.append({name!r} + ' must be ' + {f.type!r})")
            if not optional:
                lines.append(f"    if {name!r} not in payload or payload[{name!r}] is None:")
                lines.append(f"        errors.append({name!r} + ' is required')")
        lines.append("    return errors")
        lines.append("")
        lines.append(f"_VALIDATORS[{c.lower()!r}] = _check_{c.lower()}")
        lines.append("")
    lines += [
        "def validate_entity(entity: str, payload: dict[str, Any]) -> list[str]:",
        "    fn = _VALIDATORS.get(entity)",
        "    if fn is None:",
        "        return ['unknown entity: ' + entity]",
        "    return fn(payload)",
        "",
    ]
    return "\n".join(lines)


def _factory_py(ir: IR, auth: bool, health: bool) -> str:
    lines = [
        "from flask import Flask, jsonify",
        "from .routes import api",
        "",
        "def create_app() -> Flask:",
        "    app = Flask(__name__)",
        "    app.register_blueprint(api)",
    ]
    if health:
        lines += [
            "    @app.get('/health')",
            "    def health():",
            "        return jsonify({'status': 'ok'})",
        ]
    lines.append("    return app")
    lines.append("")
    return "\n".join(lines)


def _routes_py(ir: IR, auth: bool) -> str:
    lines = [
        "import os",
        "from flask import Blueprint, jsonify, request, abort",
        "from .store import list_rows, get_row, create_row, update_row, delete_row, seed",
        "from .validate import validate_entity",
        "",
        "api = Blueprint('api', __name__)",
        "",
    ]
    if auth:
        lines += [
            "def _require_auth():",
            "    token = os.environ.get('API_TOKEN', '')",
            "    if not token:",
            "        abort(503, description='API_TOKEN not configured')",
            "    if request.headers.get('Authorization') != f'Bearer {token}':",
            "        abort(401, description='invalid token')",
            "",
        ]
    for model in ir.models:
        c = pascal(model.name)
        lname = camel(model.name)
        path = f"/{plural(lname)}"
        mid = f"<{lname}_id>"
        lines.append(f"@api.get({json.dumps(path)})")
        lines.append(f"def list_{lname}():")
        lines.append(f"    return jsonify(list_rows({json.dumps(lname)}))")
        lines.append("")
        lines.append(f"@api.post({json.dumps(path)})")
        lines.append(f"def create_{lname}():")
        if auth:
            lines.append("    _require_auth()")
        lines.append("    payload = request.get_json(silent=True) or {}")
        lines.append(f"    errors = validate_entity({json.dumps(lname)}, payload)")
        lines.append("    if errors:")
        lines.append("        return jsonify({'errors': errors}), 400")
        lines.append(f"    return jsonify(create_row({json.dumps(lname)}, payload)), 201")
        lines.append("")
        lines.append(f"@api.get({json.dumps(path + '/' + mid)})")
        lines.append(f"def get_{lname}({lname}_id):")
        lines.append(f"    row = get_row({json.dumps(lname)}, {lname}_id)")
        lines.append("    if row is None:")
        lines.append("        abort(404, description='not found')")
        lines.append("    return jsonify(row)")
        lines.append("")
        lines.append(f"@api.put({json.dumps(path + '/' + mid)})")
        lines.append(f"def update_{lname}({lname}_id):")
        if auth:
            lines.append("    _require_auth()")
        lines.append("    payload = request.get_json(silent=True) or {}")
        lines.append(f"    errors = validate_entity({json.dumps(lname)}, payload)")
        lines.append("    if errors:")
        lines.append("        return jsonify({'errors': errors}), 400")
        lines.append(f"    row = update_row({json.dumps(lname)}, {lname}_id, payload)")
        lines.append("    if row is None:")
        lines.append("        abort(404, description='not found')")
        lines.append("    return jsonify(row)")
        lines.append("")
        lines.append(f"@api.delete({json.dumps(path + '/' + mid)})")
        lines.append(f"def delete_{lname}({lname}_id):")
        if auth:
            lines.append("    _require_auth()")
        lines.append(f"    if not delete_row({json.dumps(lname)}, {lname}_id):")
        lines.append("        abort(404, description='not found')")
        lines.append("    return ('', 204)")
        lines.append("")
    return "\n".join(lines)


def _test_py(ir: IR, auth: bool, health: bool) -> str:
    lines = [
        "import os",
        "import pytest",
        "from app import create_app",
        "from app.store import seed",
        "",
        "os.environ['API_TOKEN'] = 'test-token'",
        "app = create_app()",
        "",
        "@pytest.fixture(autouse=True)",
        "def _seed():\n    seed()\n",
        "def _h():\n    return {'Authorization': 'Bearer test-token'} if os.environ['API_TOKEN'] else {}\n",
        "client = app.test_client()",
        "",
    ]
    if health:
        lines += ["def test_health():\n    assert client.get('/health').status_code == 200\n"]
    for model in ir.models:
        lname = camel(model.name)
        path = f"/{plural(lname)}"
        payload = "{}" if not sample_payload(model, ir.enums, "py") else "{" + ", ".join(sample_payload(model, ir.enums, "py")) + "}"
        lines.append(f"def test_{lname}_crud():")
        lines.append(f"    created = client.post({json.dumps(path)}, json={payload}, headers=_h())")
        lines.append("    assert created.status_code == 201")
        lines.append("    row = created.get_json()")
        lines.append("    assert row['id']")
        lines.append(f"    assert client.get({json.dumps(path)}).status_code == 200")
        lines.append(f"    assert client.get({json.dumps(path + '/' + lname + '_1')}).status_code == 200")
        lines.append(f"    assert client.get({json.dumps(path + '/missing')}).status_code == 404")
        lines.append(f"    assert client.put({json.dumps(path + '/' + lname + '_1')}, json={{}}, headers=_h()).status_code == 200")
        lines.append(f"    assert client.delete({json.dumps(path + '/' + lname + '_1')}, headers=_h()).status_code == 204")
        lines.append("")
    return "\n".join(lines)