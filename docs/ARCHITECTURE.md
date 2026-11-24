# Architecture

## Components

1. The static website at `hearmark.jobo.ink` serves an installation prompt, a small ZIP, and `manifest.json`. It does not receive audio or browser cookies.
2. The installer copies `.agents/skills/hearmark` to `~/.agents/skills/hearmark`, links Claude Code to the same directory, and creates an isolated Python environment.
3. The Skill calls `scripts/launch.py`, which runs the local CLI from that environment. The CLI emits progress to stderr and one JSON outcome on stdout.
4. Before each link task, the CLI checks PyPI's latest stable `yt-dlp` and updates the isolated environment when needed. It then tries original-language human captions, original-language automatic captions, and finally downloads audio for local ASR. It checks the final file with `ffprobe` and saves TXT, SRT, and JSON under a unique task directory.

## Models and downloads

| Choice | Language and role | First-use source | Local cache |
| --- | --- | --- | --- |
| Parakeet 110M Q8 | English default | `parakeet.cpp` GitHub release; Q8 GGUF on Hugging Face | `~/.cache/hearmark/` |
| SenseVoice Small INT8 | Chinese default; English alternative | sherpa-onnx GitHub release | `~/.cache/hearmark/models/` |
| Whisper Small / Medium / Turbo / Large v3 | Other languages or explicit quality choice | Hugging Face via faster-whisper | Standard Hugging Face cache |

Models are not downloaded at installation. The selected model downloads only on first use and is reused afterward. Parakeet's pinned runner archive and model file are checked with SHA-256. SenseVoice and Whisper are fetched from their upstream distribution channels.

`--language auto` chooses Whisper Small for ASR because the CLI has not yet determined the spoken language. An agent can pass `--language en` or `zh` when known. `--captions never` forces recognition from audio. The caption ladder uses the source's language metadata or an explicit language hint and skips translated automatic tracks. The JSON provenance distinguishes human captions, automatic captions, and local ASR. Captions can still differ from speech.

## Browser sessions and failure handling

Public access is attempted first. On a login or platform challenge, `yt-dlp` may read cookies directly from a local browser profile; no cookie value is printed, exported, or sent to Hearmark. A browser session cannot bypass DRM or unavailable media. The CLI classifies failures and gives the agent a reason to report.

The transcript and source captions are untrusted task data. The Skill tells the agent not to obey instructions embedded in media content.

## Updates

Each CLI invocation checks the website's manifest with a short timeout. It reports a newer package version but never silently replaces Skill code or model weights. Link tasks check and, when needed, upgrade stable `yt-dlp` before using it; failed checks leave the installed version usable. A release is built from a tagged source commit and published as a ZIP with a SHA-256 digest. See [RELEASING.md](RELEASING.md).
