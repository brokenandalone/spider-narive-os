"""One persistent, owner-selected Ollama brain for the EXISTING Webbie.

This lets any already-installed compatible local model, including a separately
prepared Heretic-derived model, become Webbie's everyday conversational brain
without replacing Natasha, memory, agent services or native Spider OS tools.

Only an explicit owner UI interaction may change the selection. The language
model, research worker, browser, microphone and model output never write it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
import re
import stat
import tempfile

from local_models import installed_models

DEFAULT_CHOICE_PATH = Path.home() / ".config" / "spider-os" / "webbie-brain-choice.json"
MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")


def _check_path(path):
    path = Path(path).expanduser()
    parent = path.parent
    if parent.is_symlink() or path.is_symlink():
        raise PermissionError("Webbie model preference cannot use a symlink")
    if parent.exists() and (parent.stat().st_uid != os.getuid()
                            or parent.stat().st_mode & 0o022):
        raise PermissionError("Unsafe Webbie preference directory")
    if path.exists():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise PermissionError("Unsafe Webbie model preference file")
        if info.st_size > 8192:
            raise ValueError("Oversized Webbie model preference file")
    return path


def read_choice(*, path=DEFAULT_CHOICE_PATH):
    """Return the last approved model or None. No network or file writes."""
    try:
        path = _check_path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        model = data.get("model") if isinstance(data, dict) else None
        if (isinstance(data, dict) and data.get("version") == 1
                and isinstance(model, str) and MODEL_NAME.fullmatch(model)):
            return model
    except (OSError, ValueError, TypeError, UnicodeError, PermissionError):
        pass
    return None


def select_installed_model(model, *, owner_clicked=False, path=DEFAULT_CHOICE_PATH,
                           available=None):
    """Choose once from current local Ollama tags, for all subsequent sessions.

    Does NOT download/pull, train, reconfigure Ollama or restart Webbie.
    """
    if owner_clicked is not True:
        raise PermissionError("Only the owner's native model selector may change Webbie")
    if not isinstance(model, str) or not MODEL_NAME.fullmatch(model):
        raise ValueError("Invalid Ollama model name")
    names = tuple(installed_models() if available is None else available)
    if model not in names:
        raise ValueError("That model is not installed in this PC's local Ollama")
    path = _check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = _check_path(path)
    fd, temp = tempfile.mkstemp(prefix=".webbie-brain-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"version": 1, "model": model}, output)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
        temp = None
    finally:
        if temp is not None:
            os.unlink(temp)
    return model


def restore_default(*, owner_clicked=False, path=DEFAULT_CHOICE_PATH):
    """Return to the installed Spider OS default model, without deleting models."""
    if owner_clicked is not True:
        raise PermissionError("Only the owner's native model selector may reset Webbie")
    path = _check_path(path)
    path.unlink(missing_ok=True)
    return True


def model_readiness(*, path=DEFAULT_CHOICE_PATH, available=None):
    """Read-only status, including whether an active owner choice is installed."""
    owner = read_choice(path=path)
    models = tuple(installed_models() if available is None else available)
    return {
        "owner_model": owner,
        "present": bool(owner and owner in models),
        "installed": models,
        "heretic_available": tuple(model for model in models
                                   if "heretic" in model.casefold()),
    }


# The reviewed Q4 GGUF is downloaded only through direct owner opt-in.
PREBUILT_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "install_everyday_heretic.sh"


def launch_prebuilt_heretic(*, owner_clicked=False, script=PREBUILT_SCRIPT,
                           popen=None, console=None, disk_free_bytes=None):
    """Request one owner-directed download/activation terminal.

    The terminal script confirms this exact model exists in local Ollama and
    only then selects it for permanent resident conversations.
    """
    if owner_clicked is not True:
        raise PermissionError("A deliberate local owner confirmation is required")
    script = Path(script)
    if (script.is_symlink() or not script.is_file()
            or script.resolve() != PREBUILT_SCRIPT.resolve()):
        raise PermissionError("Reviewed resident Heretic setup is unavailable")
    mode = script.stat()
    if not stat.S_ISREG(mode.st_mode) or mode.st_mode & 0o022:
        raise PermissionError("Untrusted Heretic install script permissions")
    which = shutil.which if console is None else console
    if not which("konsole"):
        raise RuntimeError("Open the native Webbie lab from a desktop with Konsole")
    if not which("ollama"):
        raise RuntimeError("Local Ollama is required")
    free = (shutil.disk_usage(Path.home()).free
            if disk_free_bytes is None else disk_free_bytes)
    if free < 10 * 1024 ** 3:
        raise RuntimeError("Need at least 10 GiB free disk for the quantized model")
    runner = popen or subprocess.Popen
    runner(["konsole", "--hold", "-e", "bash", str(script),
            "--approved-by-owner"],
           stdin=subprocess.DEVNULL,
           stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL,
           start_new_session=True)
    return True
