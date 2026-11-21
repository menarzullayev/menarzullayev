"""Rebuild the README images from live public data.

    python scripts/build_profile.py            # fetch data, write data/profile-data.json and assets/*.svg
    python scripts/build_profile.py --offline  # render from the committed data only (no network)

A failed source keeps its previous value (marked stale) and prints a warning;
a source with no previous value fails the build.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import profile_data  # noqa: E402
import profile_render  # noqa: E402

ROOT = HERE.parent
FACTS = ROOT / "data" / "facts.json"
DATA = ROOT / "data" / "profile-data.json"
ASSETS = ROOT / "assets"


def main(argv: list[str]) -> int:
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    previous = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
    if "--offline" in argv:
        data, warnings = previous, []
    else:
        data, warnings = profile_data.collect(facts, previous)
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    images = profile_render.render_all(facts, data)
    ASSETS.mkdir(exist_ok=True)
    for name, svg in images.items():
        (ASSETS / name).write_text(svg, encoding="utf-8", newline="\n")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(f"wrote {len(images)} images; {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
