"""BigBack generator CLI — `python -m generator.cli spec.json outdir`.

Deterministic: same spec -> same bytes. Write is root-confined to outdir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python generator/cli.py` OR `python -m generator.cli`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.generate import materialize  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BigBack deterministic backend generator")
    parser.add_argument("spec", nargs="?", help="Path to a spec JSON (or '-' for stdin)")
    parser.add_argument("outdir", nargs="?", default=".", help="Output directory (default: current)")
    parser.add_argument("--list-frameworks", action="store_true", help="List available frameworks and exit")
    args = parser.parse_args(argv)

    if args.list_frameworks:
        from generator.frameworks import available

        print("\n".join(available()))
        return 0

    if not args.spec:
        parser.error("spec is required unless --list-frameworks is used")

    if args.spec == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(args.spec).read_text(encoding="utf-8")
    spec = json.loads(raw)

    plan = materialize(args.outdir, spec)
    if not plan.get("ok"):
        print(f"ERROR: {plan.get('error')}", file=sys.stderr)
        return 1
    print(f"generated {len(plan.get('written', []))} files -> {plan['root']}")
    for f in plan.get("written", []):
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())