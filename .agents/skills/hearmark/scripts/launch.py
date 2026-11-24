#!/usr/bin/env python3
"""Use Hearmark's installed environment when available."""

from __future__ import annotations

import os
import sys
from pathlib import Path

venv = Path.home() / ".local/share/hearmark/venv"
runtime = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
script = Path(__file__).resolve().with_name("hearmark.py")
python = runtime if runtime.is_file() else Path(sys.executable)
os.execv(str(python), [str(python), str(script), *sys.argv[1:]])
