"""Owner-driven Heretic model experiments inside Webbie's EXISTING AI Lab.

Heretic is upstream AGPL-3.0-or-later model-ablation research software:
https://github.com/p-e-w/heretic
This adapter does NOT vendor, install, download, alter Ollama, or promote any
experiment to the resident Webbie. It runs only after a deliberate visible
owner confirmation in the existing native Cognitive Center.

The experiment opens as an interactive local Konsole session and remains
separate from the always-on Webbie service and production models.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import subprocess

EXPERIMENT_MODELS = (
    "Qwen/Qwen3-0.6B",
    "Qwen/Qwen3-1.7B",
    "Qwen/Qwen3-4B-Instruct-2507",
)
RAM_GIB_TARGETS = {
    "Qwen/Qwen3-0.6B": 8,
    "Qwen/Qwen3-1.7B": 16,
    "Qwen/Qwen3-4B-Instruct-2507": 32,
}
MIN_FREE_GIB = 15
DEFAULT_VENV = Path.home() / ".local" / "share" / "spider-os" / "heretic-venv"
DEFAULT_WORKDIR = Path.home() / "Documents" / "Spider OS" / "Webbie" / "Heretic Experiments"


@dataclass(frozen=True)
class LabStatus:
    installed: bool
    executable: str
    total_ram_gib: float
    free_disk_gib: float
    console_available: bool
    explanation: str


def _trusted_executable(candidate: Path, *, base: Path) -> bool:
    """An existing, non-symlinked venv command under its expected directory."""
    try:
        if candidate.is_symlink() or base.is_symlink():
            return False
        if candidate.parent != base / "bin":
            return False
        source = candidate.stat()
        return bool(stat.S_ISREG(source.st_mode)
                    and source.st_uid == os.getuid()
                    and not source.st_mode & 0o022
                    and os.access(candidate, os.X_OK))
    except (OSError, ValueError):
        return False


def _memory_gib(meminfo=None) -> float:
    if meminfo is None:
        meminfo = Path("/proc/meminfo").read_text(encoding="ascii")
    for line in str(meminfo).splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return round(int(parts[1]) / 1024 / 1024, 1)
    return 0.0


def inspect_heretic(*, venv=DEFAULT_VENV, workdir=DEFAULT_WORKDIR,
                    meminfo=None, disk_usage=None, which=None) -> LabStatus:
    """Read-only readiness: no subprocess, downloads, or filesystem writes."""
    venv = Path(venv).expanduser()
    workdir = Path(workdir).expanduser()
    executable = venv / "bin" / "heretic"
    installed = _trusted_executable(executable, base=venv)
    which = which or shutil.which
    available_console = bool(which("konsole"))
    mem_gib = _memory_gib(meminfo)
    try:
        disk = (disk_usage or shutil.disk_usage)(
            workdir if workdir.exists() else Path.home())
        free_gib = round(disk.free / (1024 ** 3), 1)
    except (OSError, ValueError):
        free_gib = 0.0
    notes = [
        "Heretic experiment status: " + ("isolated CLI available" if installed
                                         else "not installed in isolated Webbie lab environment"),
        "System RAM: %.1f GiB; free local disk: %.1f GiB." % (mem_gib, free_gib),
        "Interactive Konsole: " + ("available" if available_console else "not available"),
        "Production Webbie remains qwen3:8b via local Ollama with Natasha.",
        "Heretic experiments are separate; no model switches, source downloads, "
        "training, GitHub pushes or changes to Webbie were performed.",
    ]
    return LabStatus(installed, str(executable), mem_gib, free_gib,
                     available_console, "\n".join(notes))


def plan_experiment(model: str, status: LabStatus) -> tuple[bool, str]:
    if model not in EXPERIMENT_MODELS:
        raise ValueError("Only a vetted Hugging Face research model is accepted")
    target = RAM_GIB_TARGETS[model]
    warnings = [
        "HERETIC EXPERIMENT: %s" % model,
        "This research modifies model refusal behavior; it does not enhance "
        "Webbie's memory, speech, knowledge, or desktop permissions.",
        "Heretic can download several gigabytes and use substantial CPU/RAM. "
        "Its interactive choices may offer to publish a model. Do NOT select "
        "publication unless you independently approve it.",
        "This will NOT change Webbie's active Ollama model, any desktop "
        "permission, the existing voice service, or saved conversations.",
        "Estimated conservative starting RAM requirement: %d GiB physical. "
        "This is a planning heuristic, not a hardware guarantee." % target,
    ]
    if not status.installed:
        warnings.append("BLOCKED: install upstream Heretic in its isolated virtual environment first.")
    if not status.console_available:
        warnings.append("BLOCKED: Konsole is unavailable.")
    if status.free_disk_gib < MIN_FREE_GIB:
        warnings.append("BLOCKED: less than %d GiB disk space available." % MIN_FREE_GIB)
    if status.total_ram_gib < target:
        warnings.append("BLOCKED: low physical RAM for this model. "
                        "Use the smaller option or a stronger machine.")
    ready = (status.installed and status.console_available
             and status.free_disk_gib >= MIN_FREE_GIB
             and status.total_ram_gib >= target)
    return ready, "\n".join(warnings)


def launch_experiment(model: str, *, approved: bool, status=None,
                      workdir=DEFAULT_WORKDIR, popen=None) -> bool:
    """Open upstream CLI only for this GUI-approved HF model, never via shell."""
    if approved is not True:
        raise PermissionError("Only a deliberate owner GUI confirmation can start a run")
    status = status or inspect_heretic(workdir=workdir)
    ready, reason = plan_experiment(model, status)
    if not ready:
        raise RuntimeError(reason)
    workdir = Path(workdir).expanduser()
    if workdir.is_symlink():
        raise PermissionError("Heretic experiment directory may not be a symlink")
    workdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if workdir.is_symlink():
        raise PermissionError("Unsafe experiment directory")
    # Interactive Heretic may ask whether to save or upload a derived model.
    # The human, NOT Webbie, sees and controls those prompts in Konsole.
    runner = popen or subprocess.Popen
    runner(
        ["konsole", "--hold", "-e", status.executable, model],
        cwd=str(workdir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return True

# A pinned in-tree setup entrypoint, never a model-generated command.
SETUP_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "setup_heretic_lab.sh"


def launch_lab_setup(*, approved: bool, script=SETUP_SCRIPT, status=None,
                     popen=None) -> bool:
    """Start the reviewed, interactive, optional install from Webbie's UI.

    This does NOT grant permission to install: the shell script also asks
    the owner to type INSTALL HERETIC before downloads begin.
    """
    if approved is not True:
        raise PermissionError("Heretic setup requires direct owner GUI approval")
    status = status or inspect_heretic()
    if not status.console_available:
        raise RuntimeError("Konsole is required for the interactive setup")
    if status.installed:
        raise RuntimeError("Heretic is already present; inspect the model lab")
    # The venv/setup can consume more space than a single model.
    if status.free_disk_gib < 25:
        raise RuntimeError("At least 25 GiB free disk is needed for Heretic setup")
    script = Path(script)
    if script.is_symlink() or not script.is_file() or script.name != "setup_heretic_lab.sh":
        raise PermissionError("Approved Spider OS setup script is unavailable")
    if script.resolve() != SETUP_SCRIPT.resolve():
        raise PermissionError("Only the packaged Spider OS setup script is permitted")
    info = script.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
        raise PermissionError("Heretic setup script is writable by untrusted users")
    runner = popen or subprocess.Popen
    runner(
        ["konsole", "--hold", "-e", "bash", str(script), "--install"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return True
