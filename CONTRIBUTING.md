# Contributing

Thanks for helping improve Hearmark. Please open an issue before a large feature or model integration so the scope and maintenance cost are clear.

## Workflow

1. Create a branch from `main` and keep the change focused.
2. Build with `python3 scripts/build.py` and check the website if you changed it.
3. For CLI changes, run `python3 -m py_compile .agents/skills/hearmark/scripts/*.py` and test a representative local file. For downloader changes, also test a public URL and a classified failure.
4. Open a pull request describing behavior, verification, and any privacy, platform, or model-license effect.

Keep `SKILL.md` short and put deterministic work in `scripts/`. Keep the canonical Skill in `.agents/skills/hearmark`; do not duplicate it into `.claude/skills`. The installer creates the Claude symlink. Avoid adding server accounts, uploads, or dependency layers without a concrete need.

We do not accept pasted cookies, access tokens, private media, or personal recordings in public issues. Use a reproducible public source or a synthetic sample. Please report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

By contributing, you agree that your contributions are licensed under the repository's MIT license.
