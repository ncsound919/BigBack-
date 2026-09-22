"""Tests for the BigBack deterministic generator. No network, no LLM."""

import json
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.core import parse_schema  # noqa: E402
from generator.generate import generate, materialize  # noqa: E402
from generator.frameworks import available  # noqa: E402

SCHEMA = """\
entity User {
  id string pk
  email string unique
  age int optional
  role Role
}
enum Role { admin member guest }
entity Post {
  id string pk
  title string
  author User optional
}
"""


def _files(plan):
    return {f["output"]: f["rendered"] for f in plan["files"]}


def _spec(framework="fastapi", schema=SCHEMA, **kw):
    s = {"project": "acme-api", "framework": framework, "schema": schema, **kw}
    return s


def test_frameworks_available():
    assert "fastapi" in available()
    assert set(available()) == {"fastapi", "express", "hono", "fastify", "flask"}


def test_parse_schema():
    ir = parse_schema(SCHEMA)
    assert [m.name for m in ir.models] == ["User", "Post"]
    assert ir.enums == {"Role": ["admin", "member", "guest"]}


def test_bad_schema_reports_honest_error():
    plan = generate(_spec(schema="entity A {}"))
    assert plan["ok"] is False
    assert "schema parse failed" in plan["error"]


def test_unknown_framework_falls_back_to_fastapi():
    plan = generate(_spec(framework="nope"))
    assert plan["framework"] == "fastapi"
    assert plan["ok"] is True


def test_every_framework_generates_full_envelope():
    for fw in available():
        plan = generate(_spec(framework=fw))
        assert plan["ok"], fw
        assert plan["framework"] == fw
        files = _files(plan)
        assert "bigback.spec.json" in files and "bigback.manifest.json" in files
        assert files["README.md"].startswith("# acme-api")
        manifest = json.loads(files["bigback.manifest.json"])
        assert set(manifest["generated"]) == set(files.keys()) - {"bigback.manifest.json"}
        # no stub markers anywhere
        for rel, body in files.items():
            assert "NOT IMPLEMENTED" not in body, fw
            assert "NotImplementedError" not in body, fw


def test_determinism():
    a = generate(_spec(framework="fastapi"))
    b = generate(_spec(framework="fastapi"))
    assert a == b
    c = generate(_spec(framework="express"))
    d = generate(_spec(framework="express"))
    assert c == d


def test_fastapi_emits_health_and_auth():
    plan = generate(_spec(framework="fastapi", auth=True, health=True))
    files = _files(plan)
    assert "app/security.py" in files
    assert "API_TOKEN" in files["app/security.py"]
    assert "/health" in files["app/main.py"]
    noauth = _files(generate(_spec(framework="fastapi", auth=False, health=False)))
    assert "app/security.py" not in noauth


def test_python_frameworks_compile(tmp_path: Path):
    for fw in ("fastapi", "flask"):
        plan = generate(_spec(framework=fw))
        assert plan["ok"], fw
        for rel, body in _files(plan).items():
            if not rel.endswith(".py"):
                continue
            p = tmp_path / rel.replace("/", "_")
            p.write_text(body, encoding="utf-8")
            py_compile.compile(str(p), doraise=True)


def test_express_routes_use_zod_and_auth_guard():
    plan = generate(_spec(framework="express"))
    files = _files(plan)
    assert "safeParse" in files["src/routes.ts"]
    assert "requireAuth" in files["src/routes.ts"]
    assert "API_TOKEN" in files["src/security.ts"]
    assert 'import { z } from "zod"' in files["src/zod.ts"]


def test_materialize_writes_confined(tmp_path: Path):
    result = materialize(str(tmp_path), _spec(framework="flask"))
    assert result["ok"]
    assert (tmp_path / "app" / "main.py").exists()
    assert (tmp_path / "tests" / "test_api.py").exists()
    # traversal refused
    plan = materialize(str(tmp_path), _spec(framework="fastapi", project="../../evil"))
    assert plan["ok"] is True  # project is sanitized; traversal via output rel is blocked
    assert all(".." not in f for f in plan["written"])


def test_cli_list_frameworks_and_stdin(tmp_path: Path):
    cli = Path(__file__).resolve().parents[1] / "generator" / "cli.py"
    out = subprocess.run(
        [sys.executable, str(cli), "--list-frameworks"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert "hono" in out.stdout

    spec = _spec(framework="fastapi")
    gen = subprocess.run(
        [sys.executable, str(cli), "-", str(tmp_path)],
        input=json.dumps(spec), capture_output=True, text=True,
    )
    assert gen.returncode == 0, gen.stderr
    assert (tmp_path / "app" / "main.py").exists()


def test_spec_normalization_project_sanitized():
    from generator.generate import normalize_spec

    cfg = normalize_spec({"project": "My Acme API!", "framework": "express"})
    assert cfg["project"] == "my-acme-api"


def test_generator_api_plan_endpoint():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    res = client.post(
        "/api/v1/generator/plan",
        json={"project": "api-test", "framework": "hono", "schema_text": SCHEMA},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["framework"] == "hono"
    assert any(f["output"] == "src/app.ts" for f in body["files"])

    fw = client.get("/api/v1/generator/frameworks")
    assert fw.status_code == 200
    assert "fastify" in fw.json()["frameworks"]