#!/usr/bin/env python3
"""Private, read-only Spider OS hardware compatibility inventory.

Never opens the camera or records microphone audio. No serials, usernames,
device IDs, paths under HOME, IP addresses or network interfaces are reported.
Presence of a tool or device does NOT prove that it functions.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess

GIB = 1024 ** 3
MIN_FREE_GIB = 5.0


def _version(path):
    try:
        details = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, value = line.split("=", 1)
                if k in ("ID", "VERSION_ID"):
                    details[k] = value.strip().strip('"')
        return {"family": details.get("ID", "unverified"),
                "version": details.get("VERSION_ID", "unverified")}
    except (OSError, UnicodeError):
        return {"family": "unverified", "version": "unverified"}


def _mem(path):
    try:
        values = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("MemTotal:", "MemAvailable:"):
                values[parts[0]] = round(int(parts[1]) * 1024 / GIB, 2)
        return {"total_gib": values.get("MemTotal:"),
                "available_gib": values.get("MemAvailable:")}
    except (OSError, ValueError, UnicodeError):
        return {"total_gib": None, "available_gib": None}


def _audio(runner, which):
    if not which("pactl"):
        return {"pipewire_input_sources": "unverified",
                "default_microphone": "unverified"}
    try:
        sources = runner(["pactl", "list", "short", "sources"],
                         capture_output=True, text=True, timeout=4, check=False)
        default = runner(["pactl", "get-default-source"],
                         capture_output=True, text=True, timeout=4, check=False)
        if sources.returncode or default.returncode:
            raise ValueError("audio status unavailable")
        # Source names are device identifiers and MUST NOT be returned.
        physical = [row.split()[1] for row in sources.stdout.splitlines()
                    if len(row.split()) >= 2 and
                    not row.split()[1].endswith(".monitor")]
        selected = default.stdout.strip()
        return {"pipewire_input_sources": "detected" if physical else "none_detected",
                "default_microphone": "selected" if selected in physical
                else "unverified"}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"pipewire_input_sources": "unverified",
                "default_microphone": "unverified"}


def inspect_hardware(*, installed_root=Path("/usr/local/lib/spider-os"),
                     os_release=Path("/etc/os-release"),
                     meminfo=Path("/proc/meminfo"),
                     dri=Path("/dev/dri"), environ=None,
                     runner=subprocess.run, which=shutil.which,
                     disk_usage=shutil.disk_usage):
    env = os.environ if environ is None else environ
    os_version = _version(os_release)
    memory = _mem(meminfo)
    session = env.get("XDG_SESSION_TYPE", "").lower()
    if session not in ("x11", "wayland"):
        session = "unverified"
    kde = "reported" if env.get("KDE_FULL_SESSION", "").lower() == "true" else "unverified"
    device = Path(dri)
    render = ("detected" if device.is_dir() and not device.is_symlink()
              and any(p.is_char_device() and not p.is_symlink()
                      for p in device.glob("renderD*"))
              else "unverified")
    try:
        mount = Path(installed_root)
        while not mount.exists() and mount != mount.parent:
            mount = mount.parent
        free_gib = round(disk_usage(mount).free / GIB, 2)
    except OSError:
        free_gib = None
    app_tools = {name: "present" if which(name) else "unverified"
                 for name in ("python3", "systemctl", "arecord", "whisper-cli",
                              "ollama", "distrobox", "konsole", "ffmpeg")}
    microphone = _audio(runner, which)
    review = []
    if os_version["family"] not in ("ubuntu",):
        review.append("Ubuntu distribution not confirmed on this session")
    if free_gib is None or free_gib < MIN_FREE_GIB:
        review.append("At least five GiB of free install-volume space not confirmed")
    if microphone["default_microphone"] != "selected":
        review.append("Default non-monitor microphone selection not confirmed")
    if session == "unverified":
        review.append("Graphical desktop session not confirmed")
    if app_tools["arecord"] != "present" or app_tools["whisper-cli"] != "present":
        review.append("Required voice capture/transcription executables not confirmed")
    return {
        "os": os_version,
        "cpu_architecture": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
        "memory": memory,
        "install_volume_free_gib": free_gib,
        "desktop_session": session,
        "kde_session": kde,
        "gpu_render_node": render,
        "microphone": microphone,
        "executables": app_tools,
        "review_flags": review,
        "physical_verification_pending": [
            "Confirm actual playback and recording with owner consent",
            "Confirm authorized Cory/Shayna voice and TV/non-owner rejection",
            "Confirm emergency STOP, wake/sleep and speaker echo behavior",
            "Confirm GPU acceleration and screen/desktop interactions",
            "Confirm Kali Bay container and only authorized security tools",
            "Confirm Nova actual playback, radio handoff and live stream state",
        ],
        "notice": "Device and executable presence does not establish working hardware.",
    }
