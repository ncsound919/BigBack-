"""Framework emitter registry for the BigBack generator."""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from ..core import IR

FRAMEWORKS = ("fastapi", "express", "hono", "fastify", "flask")

EMITTERS: Dict[str, Callable[..., Tuple[List[Dict[str, str]], List[str]]]] = {}


def _register() -> None:
    from . import express, fastapi, fastify, flask, hono

    EMITTERS["fastapi"] = fastapi.emit
    EMITTERS["express"] = express.emit
    EMITTERS["hono"] = hono.emit
    EMITTERS["fastify"] = fastify.emit
    EMITTERS["flask"] = flask.emit


_register()


def available() -> List[str]:
    return list(FRAMEWORKS)


def emit_for(framework: str, ir: IR, project: str, opts: dict) -> Tuple[List[Dict[str, str]], List[str]]:
    emit = EMITTERS.get(framework)
    if emit is None:
        raise ValueError(f"unknown framework: {framework!r}; available: {list(FRAMEWORKS)}")
    return emit(ir, project, opts)