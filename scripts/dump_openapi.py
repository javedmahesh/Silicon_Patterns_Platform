"""Dump the FastAPI OpenAPI schema as JSON (deterministic — sorted keys).

This is the source of truth for the frontend's typed API contract. No running
server is needed: it imports the app and introspects the routes.

    python scripts/dump_openapi.py            # -> frontend/openapi.json
    python scripts/dump_openapi.py -          # -> stdout (JSON only)
    python scripts/dump_openapi.py out.json   # -> out.json

The frontend wrapper (frontend/scripts/api-schema.mjs) calls this with ``-`` and
feeds the JSON to openapi-typescript to (re)generate src/lib/api/schema.ts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # import `backend` without needing an install


def main() -> None:
    from backend.main import app

    spec = app.openapi()
    payload = json.dumps(spec, indent=2, sort_keys=True) + "\n"

    target = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "frontend" / "openapi.json")
    if target == "-":
        sys.stdout.write(payload)
        return

    out = Path(target)
    out.write_text(payload, encoding="utf-8")
    schemas = spec.get("components", {}).get("schemas", {})
    print(  # to stderr so stdout stays clean when piped
        f"Wrote {out} ({len(spec.get('paths', {}))} paths, {len(schemas)} schemas)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
