#!/usr/bin/env python3
"""Read-only installed-Webbie Ollama compatibility review before ONE daily install.

Reads only two known config/code files and the local Ollama API. No service
restart, model pull, environment dump, private memory, or system modification.
An explicit --smoke issues a harmless short chat request to the ALREADY
installed model, but does not prove microphone/voice/desktop compatibility.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[1]
INSTALLED = Path("/usr/local/lib/spider-os")
TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
ROOT = "http://127.0.0.1:11434"
MAX_BYTES = 32768


def _regular_file(path, *, bound=MAX_BYTES):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Required installed or candidate file missing/unsafe")
    info = path.stat()
    if info.st_size <= 0 or info.st_size > bound:
        raise ValueError("Required file empty or oversized")
    return path.read_bytes()


def _configured(path):
    config = json.loads(_regular_file(path))
    if not isinstance(config, dict):
        raise ValueError("Webbie model configuration is not an object")
    ollama = config.get("ollama")
    name = ollama.get("model") if isinstance(ollama, dict) else None
    if not isinstance(name, str) or not TAG.fullmatch(name):
        raise ValueError("Installed Webbie's explicit chat model could not be confirmed")
    url = ollama.get("url") if isinstance(ollama, dict) else None
    if url is not None and url != ROOT + "/api/chat":
        raise ValueError("Nonlocal or modified model endpoint requires review")
    return name


def _source_profile(path):
    raw = _regular_file(path, bound=2_000_000)
    tree = ast.parse(raw, filename=str(path))
    fallback = None
    has_config_lookup = False
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DEFAULT_MODEL":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        fallback = node.value.value
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "preferred_model":
            src = ast.get_source_segment(raw.decode("utf-8"), node) or ""
            has_config_lookup = ("CONFIG_FILE" in src and "config.get" in src
                                 and "return name" in src)
    if not has_config_lookup:
        raise ValueError("Candidate model-selection logic needs manual review")
    return {"default_fallback": fallback, "sha256": hashlib.sha256(raw).hexdigest()}


def _local_json(endpoint, *, data=None, timeout=3):
    if endpoint not in ("/api/tags", "/api/chat"):
        raise ValueError("Unapproved local model endpoint")
    request = urllib.request.Request(
        ROOT + endpoint, data=(json.dumps(data).encode("utf-8") if data is not None else None),
        headers=({"Content-Type": "application/json"} if data is not None else {}),
        method=("POST" if data is not None else "GET"))
    # Ignore machine proxy variables even if configured; never follow redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            raise ValueError("Model endpoint redirected")
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with client.open(request, timeout=timeout) as response:
        if response.geturl() != ROOT + endpoint:
            raise ValueError("Model endpoint changed")
        packet = response.read(200_001)
    if len(packet) > 200_000:
        raise ValueError("Oversized local response")
    decoded = json.loads(packet.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Unexpected Ollama response")
    return decoded


def _installed_tags():
    packet = _local_json("/api/tags")
    rows = packet.get("models")
    if not isinstance(rows, list):
        raise ValueError("Ollama model inventory unavailable")
    return sorted(set(r["name"] for r in rows
                      if isinstance(r, dict) and isinstance(r.get("name"), str)
                      and TAG.fullmatch(r["name"])))


def _smoke_model(name):
    reply = _local_json("/api/chat", data={
        "model": name, "stream": False, "think": False,
        "keep_alive": "30m", "options": {"num_predict": 18},
        "messages": [{"role": "user", "content": "Reply with the word ready."}]
    }, timeout=100)
    response = reply.get("message")
    return (isinstance(response, dict)
            and isinstance(response.get("content"), str)
            and bool(response["content"].strip()))


def review(*, installed_root=INSTALLED, candidate_root=BASE,
           tags=None, run_smoke=False, smoke=None, environment=None):
    """Report only safe model name/hash/status, never private configuration."""
    errors = []
    notes = []
    installed_root, candidate_root = Path(installed_root), Path(candidate_root)
    profile = None
    chosen = None
    try:
        chosen = _configured(installed_root / "webbie/config/default.json")
    except (OSError, ValueError, UnicodeError, TypeError, json.JSONDecodeError) as exc:
        errors.append("Installed Webbie model selection unverified: " + type(exc).__name__)
    try:
        profile = _source_profile(candidate_root / "webbie/brain/brain.py")
    except (OSError, ValueError, UnicodeError, SyntaxError, TypeError) as exc:
        errors.append("Candidate model selector unverified: " + type(exc).__name__)
    try:
        current = _source_profile(installed_root / "webbie/brain/brain.py")
    except (OSError, ValueError, UnicodeError, SyntaxError, TypeError):
        current = None
        errors.append("Running Webbie model implementation not comparable")
    try:
        raw = _regular_file(candidate_root / "system/release_batch.py", bound=100000)
        tree = ast.parse(raw)
        allowlist = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(k, ast.Name) and k.id == "APP_FILES" for k in node.targets
            ):
                allowlist = ast.literal_eval(node.value)
                break
        if not isinstance(allowlist, (tuple, list)):
            raise ValueError("No safe central installer manifest")
        if any(p.startswith("webbie/config/") or p == "webbie/brain/brain.py" and p not in allowlist
               for p in allowlist):
            raise ValueError("Unexpected protected model configuration installation")
    except (OSError, ValueError, UnicodeError, SyntaxError, TypeError):
        errors.append("Candidate installer manifest could not be audited")
    env = os.environ if environment is None else environment
    explicit_env = env.get("WEBBIE_BRAIN_MODEL")
    if explicit_env:
        if not isinstance(explicit_env, str) or not TAG.fullmatch(explicit_env):
            errors.append("Invalid current-shell model override")
        elif chosen and explicit_env != chosen:
            errors.append("Current-shell model override differs from installed Webbie configuration")
        notes.append("A systemd service override may differ from the current shell; verify it without publishing secrets.")
    if chosen and profile and profile.get("default_fallback") != chosen:
        notes.append("Candidate's fallback differs from installed model. Installed config MUST remain authoritative.")
    if current and profile and current["sha256"] != profile["sha256"]:
        notes.append("Installed Webbie brain differs from candidate: requires owner-PC source reconciliation.")
    try:
        available = _installed_tags() if tags is None else tags
        if not isinstance(available, (list, tuple)) or any(
            not isinstance(n, str) or not TAG.fullmatch(n) for n in available
        ):
            raise ValueError("Invalid local model inventory")
    except (OSError, ValueError, TimeoutError, UnicodeError, urllib.error.URLError,
            json.JSONDecodeError):
        available = []
        errors.append("Local Ollama model inventory unverified")
    if chosen and chosen not in available:
        errors.append("Webbie's selected model is not present in local Ollama")
    smoke_status = "not_requested"
    if run_smoke and not errors:
        try:
            tested = _smoke_model(chosen) if smoke is None else smoke(chosen)
            smoke_status = "passed" if tested is True else "failed"
            if smoke_status != "passed":
                errors.append("Exact installed model returned no usable chat response")
        except (OSError, ValueError, TimeoutError, UnicodeError, urllib.error.URLError,
                json.JSONDecodeError):
            smoke_status = "failed"
            errors.append("Exact installed model chat smoke test failed")
    if not run_smoke:
        notes.append("Actual model inference NOT tested; rerun with --smoke before release approval.")
    notes.append("This does not verify installed voice settings, microphones, speaker authorization, GPU or Webbie conversation continuity.")
    return {
        "status": ("BLOCKED" if errors else "MODEL_SMOKE_PASSED_REVIEW_STILL_REQUIRED"
                   if smoke_status == "passed" else "REVIEW_REQUIRED"),
        "installed_chat_model": chosen,
        "installed_model_present": chosen in available if chosen else False,
        "available_model_tags": available[:50],
        "candidate_default_fallback": profile.get("default_fallback") if profile else None,
        "candidate_brain_sha256": profile.get("sha256") if profile else None,
        "installed_brain_sha256": current.get("sha256") if current else None,
        "chat_smoke": smoke_status,
        "blockers": errors, "notes": notes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, default=BASE)
    parser.add_argument("--installed-root", type=Path, default=INSTALLED)
    parser.add_argument("--smoke", action="store_true", help="Send a small LOCAL chat prompt to the exact installed model")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = review(installed_root=args.installed_root,
                    candidate_root=args.candidate_root, run_smoke=args.smoke)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["status"] + ": selected=" + str(result["installed_chat_model"]))
        for issue in result["blockers"]:
            print("BLOCKED: " + issue)
        for note in result["notes"]:
            print("NOTE: " + note)
    return 3 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
