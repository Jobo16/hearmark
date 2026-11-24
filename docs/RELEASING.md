# Releasing Hearmark

The repository's `main` branch is the source of truth. The website is a separate static deployment of the same source; do not edit its generated files directly.

1. Land reviewed changes on `main`. Update the version string in `scripts/build.py`, `.agents/skills/hearmark/scripts/hearmark.py`, `.agents/skills/hearmark/scripts/install.py`, and `CHANGELOG.md` together.
2. Run `python3 scripts/build.py`, `python3 -m py_compile .agents/skills/hearmark/scripts/*.py`, `node --check site/app.js`, and the Skill validator if available. Verify the package hash in `dist/manifest.json` matches `dist/hearmark-package.zip`.
3. Test installation in a clean temporary home, a representative local English file, a Chinese file, and a public URL. Test a failure case and verify it returns an error rather than a transcript.
4. Tag the reviewed commit as `vX.Y.Z` and push the tag. GitHub Actions builds and publishes the ZIP as a release asset.
5. Build the same commit and deploy `dist/` to the website. Check `https://hearmark.jobo.ink/manifest.json`, package download, setup prompt, and custom-domain HTTPS. The website's manifest and the GitHub release must match.
6. Announce the version and known limitations. If a release fails, fix on a new commit and use a new patch version; do not mutate a published tag.

The runtime checks the manifest on each invocation and reports an available version. It does not auto-install updates, preserving a review point before code changes on users' machines.
