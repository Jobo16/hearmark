<p align="center"><img src="site/favicon.svg" width="64" height="64" alt="Hearmark icon"></p>

# Hearmark

![CI](https://github.com/Jobo16/hearmark/actions/workflows/ci.yml/badge.svg) ![GitHub release](https://img.shields.io/github/v/release/Jobo16/hearmark) ![License: MIT](https://img.shields.io/badge/license-MIT-187e64)

**Drop a link. Get the words.** Hearmark is an open-source Agent Skill for local media transcription in Codex and Claude Code. Give your agent a YouTube, Douyin, or TikTok link, or a local audio/video file; it returns a transcript or a concrete error.

[Website and setup prompt](https://hearmark.jobo.ink/) · [Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Roadmap](docs/ROADMAP.md)

## What it does

- Prefers available platform captions for a quick transcript, or recognizes the actual audio when captions are absent or you request it.
- Saves **TXT, SRT, and JSON** locally and returns their absolute paths to the agent.
- Uses **Parakeet 110M Q8 for English**, **SenseVoice Small for Chinese**, and **Whisper Small for other or unspecified languages** by default. Whisper Medium, Turbo, and Large v3 are optional.
- Downloads each model from its original provider on first use and caches it locally. The website serves only the small Skill package and version manifest.
- Tries public media access first. If the site requires login, it can retry using a local browser session. Cookie values stay on the user's computer.
- Checks the Hearmark package version on each run; an unavailable update check does not block transcription.

Hearmark is currently a **macOS Apple Silicon beta**. It has no hosted transcription service, account, or payment flow. Access restrictions, region locks, DRM, and platform changes can prevent a download. Model output can be wrong; review important passages.

## Install

The easiest route is to copy the setup prompt from [hearmark.jobo.ink](https://hearmark.jobo.ink/) into Codex or Claude Code. The prompt has the current ZIP URL and SHA-256.

For a source checkout:

```sh
python3 .agents/skills/hearmark/scripts/install.py --manifest-url https://hearmark.jobo.ink/manifest.json
```

The installer puts the canonical Skill at `~/.agents/skills/hearmark` and creates `~/.claude/skills/hearmark` as a symlink to it. Python packages go into a separate virtual environment at `~/.local/share/hearmark/venv`. You also need `ffmpeg` and `ffprobe` on `PATH` (`brew install ffmpeg` on macOS).

Run a diagnostic and then ask your agent to transcribe a source:

```sh
python3 ~/.agents/skills/hearmark/scripts/launch.py doctor
python3 ~/.agents/skills/hearmark/scripts/launch.py transcribe /path/to/audio.m4a --language en
python3 ~/.agents/skills/hearmark/scripts/launch.py models
```

Use `--captions never` to recognize the audio instead of using platform captions. Use `--model whisper-medium` or another listed model to override the default. By default, output is written under `~/Documents/Hearmark`.

## How the project is organized

| Path | Purpose |
| --- | --- |
| [`.agents/skills/hearmark`](.agents/skills/hearmark/SKILL.md) | Agent instructions, installer, CLI, and runtime requirements |
| [`site/`](site/index.html) | Static product and installation page |
| [`scripts/build.py`](scripts/build.py) | Builds `dist/`, the ZIP, and the version manifest |
| [`docs/`](docs/ARCHITECTURE.md) | Architecture, limitations, and release process |

The project does not bundle third-party model weights or a copy of `yt-dlp`. Their licenses and terms remain with their original projects. Respect the media platform's terms and only process media you are allowed to access.

## Development

```sh
python3 scripts/build.py
python3 -m http.server 8765 --directory dist
```

CI validates Python and JavaScript syntax, Skill packaging, and the ZIP hash. Changes go through pull requests; maintainers test a representative local file and URL before a release. Tags matching `v*` build a GitHub release ZIP. The website is deployed separately after the source and release package are verified. See the [release checklist](docs/RELEASING.md).

## License

Hearmark code is [MIT licensed](LICENSE). Downloaded models and tools have their own licenses.
