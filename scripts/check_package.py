"""Verify that the website package and its manifest describe the same Skill."""

import hashlib
import json
import pathlib
import zipfile

root = pathlib.Path(__file__).resolve().parents[1] / "dist"
manifest = json.loads((root / "manifest.json").read_text())
package = root / manifest["package"]
assert hashlib.sha256(package.read_bytes()).hexdigest() == manifest["sha256"]
with zipfile.ZipFile(package) as archive:
    assert archive.testzip() is None
    assert ".agents/skills/hearmark/SKILL.md" in archive.namelist()
    assert ".agents/skills/hearmark/scripts/install.py" in archive.namelist()
for name in ("index.html", "robots.txt", "sitemap.xml", "llms.txt"):
    assert (root / name).is_file()
