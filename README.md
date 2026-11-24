<p align="center"><img src="site/favicon.svg" width="64" height="64" alt="Hearmark icon"></p>

# Hearmark

![CI](https://github.com/Jobo16/hearmark/actions/workflows/ci.yml/badge.svg) ![GitHub release](https://img.shields.io/github/v/release/Jobo16/hearmark) ![License: MIT](https://img.shields.io/badge/license-MIT-187e64)

**Drop a link. Get the words.** Hearmark is an open-source Agent Skill and local CLI for AI agents. Give your agent a YouTube, Douyin, or TikTok link, or a local audio/video file; it returns a transcript or a concrete error.

[Website and setup prompt](https://hearmark.jobo.ink/) · [Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Roadmap](docs/ROADMAP.md)

## What it does

- Prefers original-language human captions, then original-language automatic captions, then local speech recognition when captions are absent or you request audio recognition.
- Saves **TXT, SRT, and JSON** locally and returns their absolute paths to the agent.
- Uses **Parakeet 110M Q8 for English**, **SenseVoice Small for Chinese**, and **Whisper Small for other or unspecified languages** by default. Whisper Medium, Turbo, and Large v3 are optional.
- Downloads each model from its original provider on first use and caches it locally. The website serves only the small Skill package and version manifest.
- Tries public media access first. If the site requires login, it can retry using a local browser session. Cookie values stay on the user's computer.
- Checks the Hearmark package version on each run and checks the latest stable `yt-dlp` before each link task, upgrading it when needed. An unavailable update check does not block transcription.

Hearmark supports **Apple Silicon and Intel Macs, plus Windows x64**. It has no hosted transcription service, account, or payment flow. Access restrictions, region locks, DRM, and platform changes can prevent a download. Model output can be wrong; review important passages.

## Install

The easiest route is to copy the setup prompt from [hearmark.jobo.ink](https://hearmark.jobo.ink/) into your local AI agent. The prompt has the current ZIP URL and SHA-256 and asks the agent to use its own Skill discovery path.

For a source checkout:

On macOS, run `python3 .agents/skills/hearmark/scripts/install.py --manifest-url https://hearmark.jobo.ink/manifest.json`. On Windows, run `py -3 .agents/skills/hearmark/scripts/install.py --manifest-url https://hearmark.jobo.ink/manifest.json`.

The installer puts the canonical Skill at `~/.agents/skills/hearmark`. Codex, Cursor, Gemini CLI, OpenCode, and GitHub Copilot CLI discover that user-level location. For an agent with another Skill directory, pass `--agent-skills-dir <directory>`; the installer creates a symlink to the canonical Skill (a junction on Windows), without copying it. For example, Claude Code uses `--agent-skills-dir ~/.claude/skills`. You can repeat the option for multiple agents. Agents without Skill support can run the same local CLI directly if they have local command access. Remote agents need access to the same computer, runtime, and browser session to use local models and cookies.

Python packages go into a separate virtual environment at `~/.local/share/hearmark/venv`. Python 3.11 or newer and `ffmpeg`/`ffprobe` on `PATH` are required (`brew install ffmpeg` on macOS). On Windows, use the same paths relative to your user home and replace `python3` with `py -3` in the examples below.

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
| [`scripts/deploy-site.sh`](scripts/deploy-site.sh) | Deploys the static website to Jobo's Caddy server |
| [`docs/`](docs/ARCHITECTURE.md) | Architecture, limitations, and release process |

The project does not bundle third-party model weights or a copy of `yt-dlp`. Their licenses and terms remain with their original projects. Respect the media platform's terms and only process media you are allowed to access.

## Development

```sh
python3 scripts/build.py
python3 -m http.server 8765 --directory dist
```

CI validates Python and JavaScript syntax, Skill packaging, the ZIP hash, and installation on macOS and Windows. Changes go through pull requests; maintainers test a representative local file and URL before a release. Tags matching `v*` build a GitHub release ZIP. The website is deployed to Jobo's server after the source and release package are verified. See the [release checklist](docs/RELEASING.md) and [website deployment guide](docs/DEPLOYMENT.md).

## License

Hearmark code is [MIT licensed](LICENSE). Downloaded models and tools have their own licenses.
