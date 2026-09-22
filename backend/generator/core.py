"""BigBack deterministic generator — shared core.

Parses the entity DSL into an IR and provides language-neutral emitters
(models, validation, deterministic in-memory store + seed, sample payloads)
shared by every framework emitter. Stdlib only, no LLM, fully deterministic:
the same spec always yields the same bytes.

DSL:

    entity User {
      id string pk
      email string unique
      age int optional
      role Role
    }
    enum Role { admin member guest }

Field types: string, int, float, bool, datetime, uuid, any declared enum, or
any declared entity (relation). Modifiers: pk, unique, optional, list.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

KNOWN_TYPES = {"string", "int", "float", "bool", "datetime", "uuid"}
MODIFIERS = {"pk", "unique", "optional", "list"}
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ENTITY_RE = re.compile(r"entity\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}", re.I)
_ENUM_RE = re.compile(r"enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}", re.I)


@dataclass
class Field:
    name: str
    type: str
    pk: bool = False
    unique: bool = False
    optional: bool = False
    list: bool = False


@dataclass
class Model:
    name: str
    fields: List[Field] = field(default_factory=list)


@dataclass
class IR:
    models: List[Model] = field(default_factory=list)
    enums: Dict[str, List[str]] = field(default_factory=dict)


def plural(name: str) -> str:
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


def pascal(name: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", name or "Model")
    out = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return out or "Model"


def camel(name: str) -> str:
    p = pascal(name)
    return p[:1].lower() + p[1:]


def parse_schema(text: str) -> IR:
    """Parse the entity DSL. Raises ValueError on malformed input."""
    src = text or ""
    ir = IR()
    for m in _ENUM_RE.finditer(src):
        name = m.group(1)
        if not _IDENT.match(name):
            raise ValueError(f"bad enum name: {name!r}")
        values = [v for v in re.split(r"[,\s]+", m.group(2).strip()) if v]
        if not values:
            raise ValueError(f"enum {name} has no values")
        for v in values:
            if not _IDENT.match(v):
                raise ValueError(f"bad enum value {v!r} in {name}")
        ir.enums[name] = values
    names = {m.group(1) for m in _ENTITY_RE.finditer(src)}
    for m in _ENTITY_RE.finditer(src):
        name = m.group(1)
        if not _IDENT.match(name):
            raise ValueError(f"bad entity name: {name!r}")
        if name in ir.enums:
            raise ValueError(f"name collision: {name} is both entity and enum")
        model = Model(name=name)
        for lineno, raw in enumerate(m.group(2).splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            toks = line.split()
            if len(toks) < 2:
                raise ValueError(f"{name}:{lineno} field needs name + type: {line!r}")
            fname, ftype = toks[0], toks[1]
            if not _IDENT.match(fname):
                raise ValueError(f"{name}:{lineno} bad field name {fname!r}")
            if ftype not in KNOWN_TYPES and ftype not in ir.enums and ftype not in names:
                raise ValueError(f"{name}:{lineno} unknown type {ftype!r}")
            fld = Field(name=fname, type=ftype)
            for mod in toks[2:]:
                if mod not in MODIFIERS:
                    raise ValueError(f"{name}:{lineno} unknown modifier {mod!r}")
                setattr(fld, mod, True)
            if fld.pk and ftype not in ("string", "int", "uuid"):
                raise ValueError(f"{name}:{lineno} pk must be string/int/uuid")
            if fld.list and fld.pk:
                raise ValueError(f"{name}:{lineno} pk cannot be a list")
            model.fields.append(fld)
        if not model.fields:
            raise ValueError(f"entity {name} has no fields")
        ir.models.append(model)
    if not ir.models:
        raise ValueError("no entities declared (use: entity Name { field type ... })")
    return ir


def ts_type(fld: Field, enums: Dict[str, List[str]]) -> str:
    if fld.type in enums:
        base = " | ".join(json.dumps(v) for v in enums[fld.type])
    elif fld.type == "bool":
        base = "boolean"
    elif fld.type in ("int", "float"):
        base = "number"
    else:
        base = "string"
    if fld.list:
        base = f"{base}[]"
    if fld.optional and not fld.list:
        base += " | undefined"
    return base


def py_type(fld: Field, enums: Dict[str, List[str]]) -> str:
    if fld.type in enums:
        base = fld.type
    elif fld.type == "bool":
        base = "bool"
    elif fld.type == "int":
        base = "int"
    elif fld.type == "float":
        base = "float"
    elif fld.type == "datetime":
        base = "datetime"
    else:
        base = "str"
    if fld.list:
        base = f"list[{base}]"
    return base


def zod_expr(fld: Field, enums: Dict[str, List[str]]) -> str:
    if fld.type in enums:
        base = f"z.enum({json.dumps(enums[fld.type])})"
    elif fld.type == "int":
        base = "z.number().int()"
    elif fld.type == "float":
        base = "z.number()"
    elif fld.type == "bool":
        base = "z.boolean()"
    elif fld.type == "datetime":
        base = "z.string().datetime()"
    elif fld.type == "uuid":
        base = "z.string().uuid()"
    else:
        base = "z.string().min(1)"
    if fld.list:
        base = f"z.array({base})"
    if fld.optional and not fld.list:
        base += ".optional()"
    return base


def seed_value(fld: Field, var: str, enums: Dict[str, List[str]], lang: str) -> str:
    t = fld.type
    if t == "int":
        return var
    if t == "float":
        return f"{var} + 0.5"
    if t == "bool":
        return f"{var} % 2 === 0" if lang == "ts" else f"{var} % 2 == 0"
    if t == "datetime":
        return '"2026-01-01T00:00:00.000Z"' if lang == "ts" else "'2026-01-01T00:00:00.000Z'"
    if t == "uuid":
        return '"00000000-0000-4000-8000-000000000001"' if lang == "ts" else "'00000000-0000-4000-8000-000000000001'"
    if t in enums:
        q = '"' if lang == "ts" else "'"
        return f"{q}{enums[t][0]}{q}"
    if lang == "ts":
        return f'"{fld.name}-" + {var}'
    return f"'{fld.name}-{var}'"


def sample_value(fld: Field, enums: Dict[str, List[str]], lang: str) -> str:
    t = fld.type
    if t == "int":
        return "0"
    if t == "float":
        return "0.5"
    if t == "bool":
        return "true" if lang == "ts" else "True"
    if t == "datetime":
        return '"2026-01-01T00:00:00.000Z"' if lang == "ts" else "'2026-01-01T00:00:00.000Z'"
    if t == "uuid":
        return '"00000000-0000-4000-8000-000000000001"' if lang == "ts" else "'00000000-0000-4000-8000-000000000001'"
    if t in enums:
        q = '"' if lang == "ts" else "'"
        return f"{q}{enums[t][0]}{q}"
    q = '"' if lang == "ts" else "'"
    return f"{q}test-0{q}"


def sample_payload(model: Model, enums: Dict[str, List[str]], lang: str) -> List[str]:
    out: List[str] = []
    for f in model.fields:
        if f.pk or f.optional or f.list:
            continue
        q = '"' if lang == "ts" else "'"
        out.append(f"{q}{f.name}{q}: {sample_value(f, enums, lang)}")
    return out


def spec_defaults() -> Dict[str, Any]:
    return {
        "project": "my-service",
        "framework": "fastapi",
        "auth": True,
        "database": "memory",
        "cache": "none",
        "health": True,
        "schema": "entity Item {\n  id string pk\n  name string\n}\n",
    }