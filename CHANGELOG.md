# Changelog

## 0.3.0 — 2026-11-24

- Make the website's install prompt and product copy agent-neutral.
- Keep one canonical Skill and allow any agent-specific Skill directory to link to it with `--agent-skills-dir`.
- Document CLI use for local agents without Skill discovery.

## 0.2.0 — 2026-11-24

- Prefer original-language human captions, then automatic captions, then local ASR; label transcript provenance.
- Check the latest stable `yt-dlp` before link tasks and update it when needed.
- Install and run on Apple Silicon and Intel Macs and Windows x64, including platform-specific Parakeet runners and Claude Code links.
- Validate package and installer on macOS and Windows in CI.

## 0.1.1 — 2026-11-24

- Make the Skill ZIP reproducible across the website and GitHub release builds.

## 0.1.0 — 2026-11-24

- Initial macOS Apple Silicon beta.
- Agent Skill for Codex and Claude Code with a shared canonical installation.
- Local media and supported video links, captions-first flow, local browser-session fallback, and TXT/SRT/JSON output.
- Parakeet Q8, SenseVoice Small, and optional Whisper models with first-use upstream downloads.
- Static setup website and per-run package update checks.
