#!/usr/bin/env python3
"""Hearmark: local media acquisition and transcription for coding agents."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

VERSION = "0.4.0"
CONFIG = Path.home() / ".config/hearmark/config.json"
CACHE = Path.home() / ".cache/hearmark/models"
PARAKEET_DIR = Path.home() / ".cache/hearmark/parakeet"
PARAKEET_BIN = PARAKEET_DIR / ("parakeet-cli.exe" if sys.platform == "win32" else "parakeet-cli")
PARAKEET_MODEL = CACHE / "tdt_ctc-110m-q8_0.gguf"
PARAKEET_RUNNERS = {
    ("darwin", "arm64"): ("macos-metal-arm64.tar.gz", "bc97b5e6253e928d1127f48f08242324317495ef8708e31db1e09b9537d1bb74"),
    ("darwin", "x86_64"): ("macos-cpu-x64.tar.gz", "82392069ea091c896dcf86fb5d86f20d107c71f6bad4b9e79a114523d98fb643"),
    ("win32", "amd64"): ("win-cpu-x64.zip", "d74b4e857f75f91ae215c5e91ec42bf15ec84ed3a369423c134dbd6422243ed8"),
}
PARAKEET_MODEL_URL = "https://huggingface.co/mudler/parakeet-cpp-gguf/resolve/main/tdt_ctc-110m-q8_0.gguf"
PARAKEET_MODEL_SHA256 = "614feee3a990cf0e672b0314f4da0c80ae8da9094507f5ccb7c42e43b5fc5a12"
EXISTING_SENSEVOICE = Path.home() / ".cache/local-asr/models/sensevoice-small-int8"
SENSEVOICE = EXISTING_SENSEVOICE if (EXISTING_SENSEVOICE / "model.int8.onnx").is_file() else CACHE / "sensevoice-small-int8"
SENSEVOICE_ARCHIVE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
SILERO_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
MODELS = {
    "parakeet-q8": {"description": "Fast English Parakeet 110M Q8, local runner", "languages": "en"},
    "sensevoice": {"description": "Fast Chinese and English; local ONNX model", "languages": "zh,en"},
    "whisper-small": {"description": "Light multilingual Whisper", "languages": "multilingual"},
    "whisper-medium": {"description": "Balanced multilingual Whisper", "languages": "multilingual"},
    "whisper-turbo": {"description": "Larger multilingual Whisper, higher resource use", "languages": "multilingual"},
    "whisper-large-v3": {"description": "Largest Whisper quality option", "languages": "multilingual"},
}
AUTH_MARKERS = ("sign in", "log in", "login", "not a bot", "fresh cookies", "captcha", "http error 403")
TIME_RE = re.compile(r"(?P<start>\d\d:\d\d:\d\d[.,]\d{3})\s+-->\s+(?P<end>\d\d:\d\d:\d\d[.,]\d{3})")
TAG_RE = re.compile(r"<[^>]+>")


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("status") == "ok" else 1


def read_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def check_updates() -> dict:
    url = os.environ.get("HEARMARK_MANIFEST_URL") or read_config().get("manifest_url")
    if not url:
        return {"status": "unconfigured"}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": f"Hearmark/{VERSION}"})
        with urllib.request.urlopen(request, timeout=2) as response:
            manifest = json.load(response)
        latest = str(manifest.get("version", ""))
        newer = tuple(map(int, re.findall(r"\d+", latest))) > tuple(map(int, re.findall(r"\d+", VERSION)))
        update = {"status": "available" if newer else "current", "installed": VERSION, "latest": latest}
        if update["status"] == "available":
            log(f"Hearmark update available: {VERSION} -> {latest}")
        return update
    except (OSError, ValueError, TimeoutError) as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}


def is_url(value: str) -> bool:
    return value.startswith(("https://", "http://"))


def validate_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None


def browser_candidates(requested: str) -> list[str]:
    if requested == "none":
        return []
    if requested != "auto":
        return [requested]
    if sys.platform == "darwin":
        options = [
            ("chrome", Path.home() / "Library/Application Support/Google/Chrome"),
            ("safari", Path.home() / "Library/Safari"),
            ("firefox", Path.home() / "Library/Application Support/Firefox"),
            ("edge", Path.home() / "Library/Application Support/Microsoft Edge"),
            ("brave", Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"),
        ]
        return [name for name, path in options if path.exists()][:2]
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        roaming = Path(os.environ.get("APPDATA", ""))
        options = [
            ("chrome", local / "Google/Chrome/User Data"),
            ("edge", local / "Microsoft/Edge/User Data"),
            ("firefox", roaming / "Mozilla/Firefox"),
            ("brave", local / "BraveSoftware/Brave-Browser/User Data"),
        ]
        return [name for name, path in options if path.is_dir()][:2]
    return ["chrome", "firefox"]


def update_ytdlp() -> None:
    """Check PyPI's stable release before each link task; keep an offline install usable."""
    try:
        from filelock import FileLock
        from yt_dlp.version import __version__ as installed
        lock = Path.home() / ".cache/hearmark/yt-dlp-update.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(lock), timeout=30):
            request = urllib.request.Request("https://pypi.org/pypi/yt-dlp/json", headers={"User-Agent": f"Hearmark/{VERSION}"})
            with urllib.request.urlopen(request, timeout=4) as response:
                latest = json.load(response)["info"]["version"]
            if tuple(map(int, re.findall(r"\d+", latest))) <= tuple(map(int, re.findall(r"\d+", installed))):
                return
            log(f"Updating yt-dlp {installed} -> {latest} before accessing the link...")
            uv = shutil.which("uv")
            command = [uv, "pip", "install", "--python", sys.executable, "--upgrade", "yt-dlp[default]"] if uv else [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp[default]"]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    except (OSError, ValueError, KeyError, ImportError, subprocess.CalledProcessError, TimeoutError) as exc:
        log(f"Could not check or update yt-dlp ({type(exc).__name__}); trying the installed version.")


def run_ytdlp(arguments: list[str], browser: str | None = None) -> tuple[int, list[str]]:
    command = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--newline"]
    if shutil.which("node"):
        command += ["--js-runtimes", "node"]
    if browser:
        command += ["--cookies-from-browser", browser]
    command += arguments
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines: list[str] = []
    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.strip()
        if line:
            lines.append(line)
            if line.startswith(("[download]", "[info]", "WARNING:", "ERROR:")):
                log(line)
    return process.wait(), lines


def classify_error(lines: list[str]) -> tuple[str, str]:
    errors = [line for line in lines if line.startswith("ERROR:")]
    message = errors[-1] if errors else (lines[-1] if lines else "The platform did not return media")
    lower = "\n".join(lines).lower()
    if any(marker in lower for marker in AUTH_MARKERS):
        return "auth_required", message
    if "cookie" in lower and any(word in lower for word in ("decrypt", "database", "not found")):
        return "cookie_unavailable", message
    if "unavailable" in lower or "private video" in lower:
        return "unavailable", message
    return "platform_error", message


def run_with_browser_fallback(arguments: list[str], requested: str) -> tuple[int, list[str], str | None, list[str]]:
    tried: list[str] = ["public"]
    code, lines = run_ytdlp(arguments)
    if code == 0 or classify_error(lines)[0] != "auth_required":
        return code, lines, None, tried
    for browser in browser_candidates(requested):
        log(f"Platform verification required. Reading this computer's {browser} browser session locally.")
        tried.append(browser)
        code, lines = run_ytdlp(arguments, browser)
        if code == 0:
            return code, lines, browser, tried
        if classify_error(lines)[0] not in ("auth_required", "cookie_unavailable"):
            break
    return code, lines, None, tried


def parse_vtt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    segments: list[dict] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        position = next((i for i, line in enumerate(lines) if TIME_RE.search(line)), None)
        if position is None:
            continue
        match = TIME_RE.search(lines[position])
        assert match is not None
        words = " ".join(html.unescape(TAG_RE.sub("", line)) for line in lines[position + 1 :]).strip()
        if not words:
            continue
        if segments and words == segments[-1]["text"]:
            segments[-1]["end"] = match.group("end").replace(".", ",")
        else:
            segments.append({
                "start": match.group("start").replace(".", ","),
                "end": match.group("end").replace(".", ","),
                "text": words,
            })
    return segments


def caption_track(tracks: dict, spoken: str, requested: str, allow_single: bool = False) -> str | None:
    """Select a native-language track, avoiding translated automatic tracks."""
    if not isinstance(tracks, dict):
        return None
    preferred = spoken or (requested if requested != "auto" else "")
    if not preferred:
        originals = [code for code in tracks if code.endswith("-orig")]
        if originals:
            return originals[0]
        return next(iter(tracks)) if allow_single and len(tracks) == 1 else None
    base = preferred.lower().split("-")[0]
    matches = [code for code in tracks if code.lower() == preferred.lower() or code.lower().split("-")[0] == base]
    matches = [code for code in matches if code.lower() == base or code.lower().endswith("-orig") or (base == "zh" and code.lower().startswith("zh-"))]
    return matches[0] if matches else None


def try_captions(url: str, directory: Path, language: str, browser: str) -> tuple[list[dict], str | None, list[str], str | None, str | None]:
    info_arguments = ["--dump-single-json", "--skip-download", url]
    code, lines, used_browser, tried = run_with_browser_fallback(info_arguments, browser)
    if code != 0:
        return [], used_browser, tried, None, None
    try:
        info = next(json.loads(line) for line in reversed(lines) if line.startswith("{"))
    except (StopIteration, ValueError):
        return [], used_browser, tried, None, None
    spoken = str(info.get("language") or "")
    if not any(caption_track(info.get(key) or {}, spoken, language, allow_single=key == "subtitles") for key in ("subtitles", "automatic_captions")):
        for candidate in browser_candidates(browser):
            if candidate in tried:
                continue
            log(f"No usable captions were visible without a browser session. Checking this computer's {candidate} session locally.")
            tried.append(candidate)
            session_code, session_lines = run_ytdlp(info_arguments, candidate)
            if session_code != 0:
                continue
            try:
                session_info = next(json.loads(line) for line in reversed(session_lines) if line.startswith("{"))
            except (StopIteration, ValueError):
                continue
            session_spoken = str(session_info.get("language") or "")
            if any(caption_track(session_info.get(key) or {}, session_spoken, language, allow_single=key == "subtitles") for key in ("subtitles", "automatic_captions")):
                info, spoken, used_browser = session_info, session_spoken, candidate
                break
    for key, option, provenance in (("subtitles", "--write-subs", "manual_captions"), ("automatic_captions", "--write-auto-subs", "automatic_captions")):
        track = caption_track(info.get(key) or {}, spoken, language, allow_single=key == "subtitles")
        if not track:
            continue
        arguments = ["--skip-download", option, "--sub-format", "vtt", "--sub-langs", "^" + re.escape(track) + "$", "-o", str(directory / "caption.%(ext)s"), url]
        result, _lines, caption_browser, caption_tried = run_with_browser_fallback(arguments, browser)
        tried.extend(item for item in caption_tried if item not in tried)
        if caption_browser:
            used_browser = caption_browser
        if result == 0:
            for file in (*directory.glob("caption.*.vtt"), *directory.glob("caption.*.srt")):
                segments = parse_vtt(file)
                if segments:
                    return segments, used_browser, tried, provenance, track
    return [], used_browser, tried, None, None


def has_audio(path: Path) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0 and "audio" in result.stdout


def download_media(url: str, directory: Path, browser: str) -> tuple[Path, str | None, list[str]]:
    arguments = [
        "-f", "bestaudio/best", "-o", str(directory / "media.%(ext)s"),
        "--print", "after_move:filepath", url,
    ]
    code, lines, used_browser, tried = run_with_browser_fallback(arguments, browser)
    if code != 0:
        kind, message = classify_error(lines)
        raise MediaError(kind, message, tried)
    paths = [Path(line) for line in lines if line.startswith(str(directory)) and Path(line).is_file()]
    path = paths[-1] if paths else next(iter(directory.glob("media.*")), None)
    if path is None or not path.is_file() or path.stat().st_size == 0 or not has_audio(path):
        raise MediaError("invalid_media", "Downloaded file is empty or has no audio stream", tried)
    return path, used_browser, tried


class MediaError(Exception):
    def __init__(self, kind: str, message: str, tried: list[str] | None = None):
        super().__init__(message)
        self.kind = kind
        self.tried = tried or []


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise MediaError("download_mismatch", f"Downloaded file did not match its published SHA-256: {path.name}")


def ensure_parakeet() -> None:
    if not PARAKEET_BIN.is_file():
        runner = PARAKEET_RUNNERS.get((sys.platform, platform.machine().lower()))
        if runner is None:
            raise MediaError("unsupported_platform", "Parakeet runner supports Apple Silicon and Intel Macs or Windows x64")
        archive_name, expected_sha = runner
        log("Downloading Parakeet's local runner for first use...")
        with tempfile.TemporaryDirectory(prefix="hearmark-parakeet-") as temp:
            archive = Path(temp) / archive_name
            download_file("https://github.com/mudler/parakeet.cpp/releases/download/v0.6.1/parakeet-v0.6.1-bin-" + archive_name, archive)
            verify_sha256(archive, expected_sha)
            suffix = "/" + PARAKEET_BIN.name
            if archive_name.endswith(".zip"):
                with zipfile.ZipFile(archive) as package:
                    member = next((name for name in package.namelist() if name.endswith(suffix)), None)
                    if member is None:
                        raise MediaError("model_download_failed", "Parakeet runner archive is incomplete")
                    data = package.read(member)
            else:
                with tarfile.open(archive, "r:gz") as package:
                    member = next((item for item in package if item.isfile() and item.name.endswith(suffix)), None)
                    if member is None:
                        raise MediaError("model_download_failed", "Parakeet runner archive is incomplete")
                    source = package.extractfile(member)
                    assert source is not None
                    data = source.read()
            PARAKEET_DIR.mkdir(parents=True, exist_ok=True)
            partial = PARAKEET_BIN.with_suffix(PARAKEET_BIN.suffix + ".part")
            partial.write_bytes(data)
            partial.chmod(0o755)
            os.replace(partial, PARAKEET_BIN)
    if not PARAKEET_MODEL.is_file():
        log("Downloading Parakeet 110M Q8 weights from Hugging Face for first use...")
        partial = PARAKEET_MODEL.with_suffix(".gguf.part")
        try:
            download_file(PARAKEET_MODEL_URL, partial)
            verify_sha256(partial, PARAKEET_MODEL_SHA256)
            os.replace(partial, PARAKEET_MODEL)
        finally:
            partial.unlink(missing_ok=True)


def transcribe_parakeet(path: Path) -> list[dict]:
    ensure_parakeet()
    with tempfile.TemporaryDirectory(prefix="hearmark-audio-") as temp:
        wav = Path(temp) / "audio.wav"
        conversion = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
            capture_output=True, text=True, check=False,
        )
        if conversion.returncode != 0:
            raise MediaError("invalid_media", "Could not decode the audio for Parakeet")
        result = subprocess.run(
            [str(PARAKEET_BIN), "transcribe", "--model", str(PARAKEET_MODEL), "--input", str(wav),
             "--threads", "2", "--decoder", "tdt", "--json"],
            capture_output=True, text=True, check=False,
        )
    if result.returncode != 0:
        raise MediaError("processing_failed", result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "Parakeet failed")
    payload = next((json.loads(line) for line in reversed(result.stdout.splitlines()) if line.startswith("{\"text\"")), None)
    if payload is None:
        raise MediaError("processing_failed", "Parakeet returned no transcript")
    words = payload.get("words", [])
    if not words:
        return []
    segments: list[dict] = []
    group: list[dict] = []
    for word in words:
        if group and (float(word["start"]) - float(group[-1]["end"]) > 1.5 or float(word["end"]) - float(group[0]["start"]) > 8):
            segments.append({"start": seconds_to_srt(group[0]["start"]), "end": seconds_to_srt(group[-1]["end"]), "text": " ".join(item["w"] for item in group)})
            group = []
        group.append(word)
        if str(word["w"]).endswith((".", "?", "!")):
            segments.append({"start": seconds_to_srt(group[0]["start"]), "end": seconds_to_srt(group[-1]["end"]), "text": " ".join(item["w"] for item in group)})
            group = []
    if group:
        segments.append({"start": seconds_to_srt(group[0]["start"]), "end": seconds_to_srt(group[-1]["end"]), "text": " ".join(item["w"] for item in group)})
    return segments


def ensure_sensevoice() -> None:
    needed = [SENSEVOICE / "model.int8.onnx", SENSEVOICE / "tokens.txt", SENSEVOICE / "silero_vad.onnx"]
    if all(path.is_file() for path in needed):
        return
    log("Downloading SenseVoice Small model for first use...")
    with tempfile.TemporaryDirectory(prefix="hearmark-model-") as temp:
        archive = Path(temp) / "sensevoice.tar.bz2"
        download_file(SENSEVOICE_ARCHIVE, archive)
        SENSEVOICE.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r:bz2") as package:
            for name in ("model.int8.onnx", "tokens.txt"):
                member = next((item for item in package if item.isfile() and item.name.endswith("/" + name)), None)
                if member is None:
                    raise MediaError("model_download_failed", f"SenseVoice archive is missing {name}")
                source = package.extractfile(member)
                assert source is not None
                with source, (SENSEVOICE / (name + ".part")).open("wb") as output:
                    shutil.copyfileobj(source, output)
                os.replace(SENSEVOICE / (name + ".part"), SENSEVOICE / name)
        download_file(SILERO_URL, SENSEVOICE / "silero_vad.onnx.part")
        os.replace(SENSEVOICE / "silero_vad.onnx.part", SENSEVOICE / "silero_vad.onnx")


def transcribe_sensevoice(path: Path) -> list[dict]:
    import numpy as np
    import sherpa_onnx
    from faster_whisper import decode_audio

    ensure_sensevoice()
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(SENSEVOICE / "model.int8.onnx"),
        tokens=str(SENSEVOICE / "tokens.txt"),
        num_threads=2, language="auto", use_itn=True,
    )
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(SENSEVOICE / "silero_vad.onnx")
    config.silero_vad.min_silence_duration = 0.5
    config.silero_vad.max_speech_duration = 10.0
    config.silero_vad.window_size = 512
    config.sample_rate = 16000
    detector = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=120)
    audio = decode_audio(str(path), sampling_rate=16000)
    pieces: list[tuple[int, object]] = []
    def collect() -> None:
        while not detector.empty():
            part = detector.front
            pieces.append((int(part.start), np.asarray(part.samples)))
            detector.pop()
    for offset in range(0, len(audio), 512):
        detector.accept_waveform(audio[offset : offset + 512])
        collect()
    if detector.is_speech_detected():
        for _ in range(64):
            detector.accept_waveform(np.zeros(512, dtype=np.float32))
            if not detector.is_speech_detected():
                break
        collect()
    segments: list[dict] = []
    for start, samples in pieces:
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        recognizer.decode_stream(stream)
        words = stream.result.text.strip()
        if words:
            segments.append({
                "start": seconds_to_srt(start / 16000),
                "end": seconds_to_srt((start + len(samples)) / 16000),
                "text": words,
            })
    return segments


def seconds_to_srt(seconds: float) -> str:
    millis = round(seconds * 1000)
    hour, millis = divmod(millis, 3_600_000)
    minute, millis = divmod(millis, 60_000)
    second, millis = divmod(millis, 1000)
    return f"{hour:02}:{minute:02}:{second:02},{millis:03}"


def transcribe_whisper(path: Path, model_name: str, language: str) -> list[dict]:
    from faster_whisper import WhisperModel

    name = {"whisper-turbo": "large-v3-turbo", "whisper-large-v3": "large-v3"}.get(model_name, model_name.removeprefix("whisper-"))
    log(f"Loading {model_name}; first use may download model weights...")
    model = WhisperModel(name, device="auto", compute_type="auto", cpu_threads=4)
    stream, _info = model.transcribe(str(path), language=None if language == "auto" else language, vad_filter=True)
    return [
        {"start": seconds_to_srt(part.start), "end": seconds_to_srt(part.end), "text": part.text.strip()}
        for part in stream if part.text.strip()
    ]


def choose_model(requested: str, language: str) -> str:
    if requested != "auto":
        return requested
    return "parakeet-q8" if language == "en" else "sensevoice" if language == "zh" else "whisper-small"


def write_transcript(directory: Path, segments: list[dict], metadata: dict) -> dict:
    if not segments:
        raise MediaError("no_speech", "No speech or usable captions were found")
    separator = "" if metadata.get("language") == "zh" else " "
    text = separator.join(item["text"] for item in segments)
    transcript = directory / "transcript.txt"
    subtitles = directory / "transcript.srt"
    details = directory / "transcript.json"
    transcript.write_text(text + "\n", encoding="utf-8")
    subtitles.write_text("\n".join(
        f"{index}\n{part['start']} --> {part['end']}\n{part['text']}\n"
        for index, part in enumerate(segments, 1)
    ), encoding="utf-8")
    details.write_text(json.dumps({**metadata, "segments": segments}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"transcript": str(transcript), "subtitles": str(subtitles), "metadata": str(details), "characters": len(text)}


def transcribe(args: argparse.Namespace, update: dict) -> int:
    if not shutil.which("ffprobe"):
        return emit({"status": "error", "kind": "missing_dependency", "message": "ffmpeg/ffprobe is required", "update": update})
    source = args.source
    if is_url(source) and not validate_url(source):
        return emit({"status": "error", "kind": "unsupported_url", "message": "Use one HTTPS link supported by yt-dlp, or a local audio/video file", "update": update})
    if not is_url(source) and not Path(source).expanduser().is_file():
        return emit({"status": "error", "kind": "missing_file", "message": "Local media file was not found", "update": update})
    output_root = args.output_dir.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha256(source.encode()).hexdigest()[:8]
    directory = output_root / (time.strftime("%Y%m%d-%H%M%S") + "-" + tag + "-" + os.urandom(2).hex())
    directory.mkdir(exist_ok=False)
    tried: list[str] = []
    used_browser: str | None = None
    try:
        if is_url(source):
            update_ytdlp()
            if args.captions == "prefer":
                segments, used_browser, tried, caption_origin, caption_language = try_captions(source, directory, args.language, args.browser)
                if segments:
                    files = write_transcript(directory, segments, {
                        "source": source, "provenance": caption_origin, "model": None,
                        "language": caption_language, "browser": used_browser,
                    })
                    return emit({"status": "ok", **files, "directory": str(directory), "provenance": caption_origin, "update": update})
            media, used_browser, tried = download_media(source, directory, args.browser)
        else:
            media = Path(source).expanduser().resolve()
        model = choose_model(args.model, args.language)
        if model == "parakeet-q8" and args.language not in ("auto", "en"):
            raise MediaError("unsupported_language", "Parakeet Q8 recognizes English only; choose SenseVoice or Whisper for other languages")
        if model == "sensevoice" and args.language not in ("auto", "en", "zh"):
            raise MediaError("unsupported_language", "SenseVoice option is for English and Chinese; choose a Whisper model")
        if model == "parakeet-q8":
            segments = transcribe_parakeet(media)
        elif model == "sensevoice":
            segments = transcribe_sensevoice(media)
        else:
            segments = transcribe_whisper(media, model, args.language)
        files = write_transcript(directory, segments, {
            "source": source, "media": str(media), "provenance": "local_asr",
            "model": model, "language": args.language, "browser": used_browser,
        })
        return emit({"status": "ok", **files, "directory": str(directory), "media": str(media), "model": model, "provenance": "local_asr", "update": update})
    except MediaError as exc:
        return emit({"status": "error", "kind": exc.kind, "message": str(exc), "tried": exc.tried or tried, "directory": str(directory), "update": update})
    except (OSError, RuntimeError, ImportError, ValueError) as exc:
        return emit({"status": "error", "kind": "processing_failed", "message": str(exc), "tried": tried, "directory": str(directory), "update": update})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    transcribe_parser = sub.add_parser("transcribe", help="Transcribe a URL or local file")
    transcribe_parser.add_argument("source")
    transcribe_parser.add_argument("--output-dir", type=Path, default=Path.home() / "Documents/Hearmark")
    transcribe_parser.add_argument("--language", default="auto")
    transcribe_parser.add_argument("--model", choices=("auto", *MODELS), default="auto")
    transcribe_parser.add_argument("--captions", choices=("prefer", "never"), default="prefer")
    transcribe_parser.add_argument("--browser", choices=("auto", "none", "chrome", "safari", "firefox", "edge", "brave"), default="auto")
    sub.add_parser("models", help="List model options")
    sub.add_parser("doctor", help="Check local dependencies")
    sub.add_parser("check-updates", help="Check the published package version")
    args = parser.parse_args()
    update = check_updates()
    if args.command == "transcribe":
        return transcribe(args, update)
    if args.command == "models":
        return emit({"status": "ok", "models": MODELS, "auto": "Parakeet Q8 for en; SenseVoice for zh; Whisper small otherwise", "update": update})
    if args.command == "doctor":
        modules = {}
        for name in ("yt_dlp", "faster_whisper", "sherpa_onnx"):
            try:
                __import__(name)
                modules[name] = True
            except ImportError:
                modules[name] = False
        ready = bool(shutil.which("ffprobe")) and bool(shutil.which("ffmpeg")) and all(modules.values())
        return emit({"status": "ok" if ready else "error", "kind": None if ready else "missing_dependency", "version": VERSION, "ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")), "modules": modules, "parakeet_cached": PARAKEET_MODEL.is_file() and PARAKEET_BIN.is_file(), "sensevoice_cached": (SENSEVOICE / "model.int8.onnx").is_file(), "update": update})
    return emit({"status": "ok", "version": VERSION, "update": update})


if __name__ == "__main__":
    raise SystemExit(main())
