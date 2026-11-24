# Releasing Hearmark

The repository's `main` branch is the source of truth. The website is served from Jobo's Caddy server; do not edit its generated files directly.

1. Land reviewed changes on `main`. Update the version string in `scripts/build.py`, `.agents/skills/hearmark/scripts/hearmark.py`, `.agents/skills/hearmark/scripts/install.py`, and `CHANGELOG.md` together.
2. Run `python scripts/build.py`, `python -m compileall -q .agents/skills/hearmark/scripts`, `python -m unittest discover -s tests -q`, `node --check site/app.js`, and `python scripts/check_package.py`. Run the Skill validator if available.
3. Check CI installation on macOS and Windows. Test a representative local English file, a Chinese file, and a public URL. Test a failure case and verify it returns an error rather than a transcript.
4. Tag the reviewed commit as `vX.Y.Z` and push the tag. GitHub Actions builds and publishes the ZIP as a release asset.
5. Run `bash scripts/deploy-site.sh` from the same commit. Check `https://hearmark.jobo.ink/manifest.json`, package download, setup prompt, and HTTPS. The website's manifest and the GitHub release must match.
6. Announce the version and known limitations. If a release fails, fix on a new commit and use a new patch version; do not mutate a published tag.

The runtime checks the manifest on each invocation and reports an available version. It does not auto-install updates, preserving a review point before code changes on users' machines.
