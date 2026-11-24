#!/usr/bin/env python3
"""Build the static Hearmark page and its agent-installable package."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "0.4.0"


def main() -> None:
    DIST.mkdir(exist_ok=True)
    for name in ("index.html", "style.css", "app.js", "favicon.svg", "robots.txt", "sitemap.xml", "llms.txt"):
        shutil.copy2(ROOT / "site" / name, DIST / name)
    package = DIST / "hearmark-package.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as output:
        for file in sorted((ROOT / ".agents/skills/hearmark").rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                info = zipfile.ZipInfo(file.relative_to(ROOT).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o644 << 16
                output.writestr(info, file.read_bytes())
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    manifest = {
        "name": "Hearmark",
        "version": VERSION,
        "platform": "macOS (Apple Silicon and Intel), Windows x64",
        "package": "hearmark-package.zip",
        "sha256": digest,
        "bytes": package.stat().st_size,
    }
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
