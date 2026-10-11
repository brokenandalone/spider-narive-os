"""Local-first proactive health checks for Webbie on Spider OS.

Only reads local machine state; never browses, captures cameras, launches
programs, approves desktop actions or transmits telemetry. The caller owns
all user-facing notifications. A health check is NOT a real AA/NA meeting
lookup or a personal-calendar connection.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
from urllib.request import urlopen

DEFAULT_STATE = Path.home() / ".local/state/spider-os/webbie-proactive.json"
MAX_STATE_BYTES = 32768
SERVICE_ALLOWLIST = frozenset({"spider-ai-dj.service", "webbie.service"})
CHECK_IDS = ("disk", "ollama", "microphone", "ai_dj")
DEFAULT_CONFIG = {
    "enabled": True,
    "check_in_minutes": 45,
    "alert_cooldown_minutes": 180,
    "quiet_start": "22:00",
    "quiet_end": "08:00",
    "disk_warning_free_gib": 5,
    "watch_ai_dj": False,
    "notify_recovery": True,
}


def configure(raw):
    """Clamped, intentionally limited user settings; never execute config."""
    data = dict(DEFAULT_CONFIG)
    if isinstance(raw, dict):
        for key in ("enabled", "watch_ai_dj", "notify_recovery"):
            if type(raw.get(key)) is bool:
                data[key] = raw[key]
        for key, low, high in (
            ("check_in_minutes", 5, 1440),
            ("alert_cooldown_minutes", 30, 1440),
            ("disk_warning_free_gib", 1, 100),
        ):
            if type(raw.get(key)) is int:
                data[key] = max(low, min(high, raw[key]))
        for key in ("quiet_start", "quiet_end"):
            value = raw.get(key)
            if isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                data[key] = value
    return data


def quiet_now(now, start, end):
    """Local clock with a midnight-spanning interval. Equal times means off."""
    current = datetime.fromtimestamp(now).strftime("%H:%M")
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _read_small_json(path):
    try:
        path = Path(path)
        if path.is_symlink():
            return {}
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_size > MAX_STATE_BYTES):
            return {}
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _store_private_json(path, value):
    path = Path(path)
    parent = path.parent
    if parent.is_symlink():
        raise PermissionError("Unsafe Webbie status folder")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = parent.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022):
        raise PermissionError("Webbie status folder must be private")
    if path.is_symlink():
        raise PermissionError("Unsafe Webbie status file")
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    if len(payload) > MAX_STATE_BYTES:
        raise ValueError("Webbie proactive state is too large")
    fd, temporary = tempfile.mkstemp(prefix=".webbie-check-", dir=parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as writer:
            writer.write(payload)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def probe_disk(*, folder=None, warning_gib=5):
    """Measure the actual HOME filesystem without walking user files."""
    location = Path(folder) if folder is not None else Path.home()
    result = shutil.disk_usage(location)
    total = max(result.total, 1)
    free_gib = result.free / (1024 ** 3)
    occupied = round((1 - result.free / total) * 100)
    low = free_gib < warning_gib or result.free / total < 0.06
    if low:
        return "warn", f"Storage is low: {free_gib:.1f} GiB free ({occupied}% used)."
    return "ok", f"Storage healthy: {free_gib:.1f} GiB free."


def probe_ollama(*, opener=urlopen):
    """Only request the fixed localhost Ollama endpoint, never a model prompt."""
    try:
        with opener("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            if response.status != 200:
                raise ValueError("Ollama is not ready")
            data = json.loads(response.read(16384))
            if not isinstance(data, dict) or not isinstance(data.get("models"), list):
                raise ValueError("Invalid Ollama status")
        return "ok", "Local Ollama is responding."
    except (OSError, ValueError, TimeoutError):
        return "warn", "Local Ollama is not responding; Webbie's AI replies may be unavailable."


def probe_microphone(*, agent_state):
    """Only inspect the resident agent's status; not actual speech capture."""
    status = _read_small_json(agent_state)
    if status.get("voice_listener") is False:
        return "warn", "Webbie reported a microphone listener error. Check its service log."
    if status.get("voice_listener") is True:
        return "ok", "Webbie's microphone listener reports running (not hardware verified)."
    return "unknown", "Microphone listener status has not been reported."


def probe_ai_dj(*, runner=subprocess.run):
    """Read-only systemd service query; optional, never starts/stops broadcasts."""
    args = ["systemctl", "--user", "is-active", "spider-ai-dj.service"]
    try:
        result = runner(args, text=True, capture_output=True, timeout=3, check=False)
        if result.returncode == 0 and result.stdout.strip() == "active":
            return "ok", "The BCN AI DJ user service is active (broadcast not verified)."
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "warn", "The BCN AI DJ user service is not active; this does not prove radio is off-air."



def request_check_now(path=DEFAULT_STATE, *, clock=None):
    """Trusted local GUI button: request read-only probes on the next tick.

    No direct access to microphones, model prompts or desktop control.
    This marker is data only, never a command interpreter.
    """
    target = Path(str(path) + ".request")
    _store_private_json(target, {"check_now": True, "requested": float(
        (clock or time.time)())})
    return True


def _take_check_request(path, now, last):
    """Honor a recent owner-local request after a 30-second safety throttle."""
    marker = Path(str(path) + ".request")
    value = _read_small_json(marker)
    requested = value.get("requested")
    if (value.get("check_now") is not True
            or not isinstance(requested, (int, float))):
        return False
    if (requested > now + 60 or now - requested > 3600):
        try:
            marker.unlink()
        except OSError:
            pass
        return False
    if now - last < 30:
        return False
    try:
        marker.unlink()
    except OSError:
        return False
    return True



class ProactiveMonitor:
    """Bounded checks + persistent change detection with no repeated alert spam."""

    def __init__(self, *, state_path=DEFAULT_STATE, agent_state=None, settings=None,
                 clock=None, checks=None, on_alert=None):
        self.path = Path(state_path)
        self.agent_state = Path(agent_state or
                                Path.home() / ".local/state/spider-os/webbie.json")
        self.settings = configure(settings)
        self.clock = clock or time.time
        self.on_alert = on_alert
        self.checks = checks
        self.state = _read_small_json(self.path)
        if not isinstance(self.state.get("checks"), dict):
            self.state["checks"] = {}
        if not isinstance(self.state.get("pending"), list):
            self.state["pending"] = []
        self.state["version"] = 1

    def _collect(self):
        if self.checks is not None:
            return self.checks()
        observations = {
            "disk": lambda: probe_disk(
                warning_gib=self.settings["disk_warning_free_gib"]),
            "ollama": probe_ollama,
            "microphone": lambda: probe_microphone(agent_state=self.agent_state),
        }
        if self.settings["watch_ai_dj"]:
            observations["ai_dj"] = probe_ai_dj
        results = {}
        for key, fn in observations.items():
            try:
                results[key] = fn()
            except Exception:
                results[key] = ("unknown", f"{key} health check could not complete.")
        return results

    def tick(self, *, session_active=False, sleeping=False):
        """Perform due checks, record outcomes, emit only eligible notifications.

        Monitoring always continues through sleep/quiet hours. Notifications
        wait until the owner is active and awake. Due times live on disk so a
        service restart does not immediately repeat successful checks.
        """
        now = float(self.clock())
        if not self.settings["enabled"]:
            self.state["enabled"] = False
            _store_private_json(self.path, self.state)
            return self.snapshot()
        self.state["enabled"] = True
        last = self.state.get("last_run", 0)
        if not isinstance(last, (int, float)) or last > now:
            last = 0
        due = now - last >= self.settings["check_in_minutes"] * 60
        # GUI-triggered read-only checks cannot run more often than once
        # every 30 seconds, even if the button is clicked repeatedly.
        requested = _take_check_request(self.path, now, last)
        if due or requested:
            results = self._collect()
            if not isinstance(results, dict):
                results = {}
            current = self.state["checks"]
            pending = {p for p in self.state["pending"] if p in CHECK_IDS}
            for key in CHECK_IDS:
                if key not in results:
                    continue
                status, message = results[key]
                if status not in {"ok", "warn", "unknown"}:
                    continue
                # Only built-in check IDs; external test probes are still
                # normalized. Never feed model responses to alerts.
                message = str(message or "")[:240].replace("\n", " ")
                previous = current.get(key, {})
                old = previous.get("status")
                last_alert = previous.get("last_alert", 0)
                if not isinstance(last_alert, (int, float)):
                    last_alert = 0
                if status == "warn":
                    if old != "warn" or now - last_alert >= self.settings["alert_cooldown_minutes"] * 60:
                        pending.add(key)
                elif status == "ok":
                    # Recoveries notify only if the earlier warning was
                    # genuinely delivered. No ghosts from transient alerts.
                    pending.discard(key)
                    if (old == "warn" and previous.get("alerted") is True
                            and self.settings["notify_recovery"]):
                        pending.add(key)
                else:
                    pending.discard(key)
                current[key] = {
                    "status": status, "message": message, "checked_at": now,
                    "last_alert": last_alert, "alerted": previous.get("alerted") is True,
                }
            self.state["pending"] = sorted(pending)
            self.state["last_run"] = now
        quiet = quiet_now(now, self.settings["quiet_start"], self.settings["quiet_end"])
        if session_active is True and sleeping is False and not quiet:
            for key in list(self.state["pending"]):
                record = self.state["checks"].get(key)
                if not isinstance(record, dict):
                    self.state["pending"].remove(key)
                    continue
                message = str(record.get("message", ""))[:240]
                if not message:
                    self.state["pending"].remove(key)
                    continue
                try:
                    if self.on_alert is not None:
                        self.on_alert(message)
                    else:
                        # Leave the alert pending until a notification sink
                        # is connected. A read-only checker must not discard.
                        continue
                except Exception:
                    # Preserve pending alerts when desktop notifications fail.
                    continue
                record["last_alert"] = now
                record["alerted"] = record.get("status") == "warn"
                self.state["pending"].remove(key)
        self.state["updated"] = now
        _store_private_json(self.path, self.state)
        return self.snapshot()

    def snapshot(self):
        data = {
            "enabled": self.state.get("enabled", self.settings["enabled"]),
            "last_run": self.state.get("last_run"),
            "pending_count": len(self.state.get("pending", [])),
            "checks": {},
        }
        for key in CHECK_IDS:
            record = self.state["checks"].get(key)
            if isinstance(record, dict):
                data["checks"][key] = {
                    "status": record.get("status", "unknown"),
                    "message": str(record.get("message", ""))[:240],
                    "checked_at": record.get("checked_at"),
                }
        return data


def read_status(path=DEFAULT_STATE):
    """Read-only status for Webbie's text/chat panel; never run checks on demand."""
    monitor = ProactiveMonitor(state_path=path, settings={"enabled": False})
    return monitor.snapshot()


def status_message(path=DEFAULT_STATE):
    snapshot = read_status(path)
    if not snapshot["last_run"]:
        return "Webbie's proactive checks haven't completed yet."
    lines = []
    for key in CHECK_IDS:
        item = snapshot["checks"].get(key)
        if item:
            lines.append(item["message"])
    if not lines:
        return "No proactive check results are available yet."
    if snapshot["pending_count"]:
        lines.append(f"{snapshot['pending_count']} alert(s) waiting for a safe time to notify you.")
    return "Last local checks: " + " ".join(lines)
