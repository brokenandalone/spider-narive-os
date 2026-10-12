#!/usr/bin/env python3
"""Propose just the reviewed native Nova Australian-voice delta, OFFLINE.

Owner's installed `media/ai-dj/service.py` is kept as the base. Only an
import, `make_audio`, the GET voices route and `do_POST` voice selection
change in the separate PRIVATE proposed copy. The host, DJ request schema,
health response, model and broadcast timing are preserved. No installation,
service restart or changes to the Spider Media Center application or BCN site.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
from pathlib import Path
import sys

from build_owner_preserving_stage import checked_path, load_owner_zip

NAME = "media/ai-dj/service.py"
PIN = "5a59dca3f83a4cc7b9c49af5b3fa5a1cf0d4eb2c3652445cf17ae4898dc96089"
IMPORT_BASE = "from nova_host import NovaHost, HOST as ON_AIR_HOST, STATION as STATION_NAME"
IMPORT_NEW = "from nova_voice import synthesize, available_profiles, normalize_voice, configured_voice"
VOICE_HELPER = "media/ai-dj/nova_voice.py"
VOICE_HELPER_SHA = "66b352f3aab9e6ff584fb95751e3bd5b308509bf"


def replace_once(content: str, old: str, new: str, label: str):
    if content.count(old) != 1:
        raise ValueError("Native Nova " + label + " no longer matches reviewed source")
    return content.replace(old, new, 1)


def methods(source: bytes):
    tree = ast.parse(source.decode("utf-8"), filename=NAME)
    output = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            output[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.ClassDef) and node.name == "Handler":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    output["Handler." + child.name] = ast.dump(child, include_attributes=False)
    return output


def propose(raw: bytes, voice_module: bytes, *, pin=PIN, helper_pin=VOICE_HELPER_SHA):
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError("Owner Nova service has changed; no safe automatic merge")
    if hashlib.sha1(voice_module).hexdigest() != helper_pin:
        # Git SHA-1 is the blob's header-prefixed hash, not bytes hash.
        git_blob_sha = hashlib.sha1(
            ("blob " + str(len(voice_module)) + "\0").encode() + voice_module
        ).hexdigest()
        if git_blob_sha != helper_pin:
            raise ValueError("Native Nova voice helper does not match reviewed Git blob")
    old = methods(raw)
    text = raw.decode("utf-8")
    text = replace_once(text,IMPORT_BASE,
                        IMPORT_BASE + "\n" + IMPORT_NEW,
                        "voice helper import")
    text = replace_once(
        text,
        """def make_audio(text, ident):
    edge = Path("/opt/spider-webbie/bin/edge-tts")""",
        """def make_audio(text, ident, profile=None):
    edge = Path("/opt/spider-webbie/bin/edge-tts")""",
        "make_audio signature",
    )
    # Replace precisely the old make_audio function, leaving all other
    # owner functions, personal configuration and HTTP handler source alone.
    previous = ast.parse(text)
    func = next(n for n in previous.body
                if isinstance(n, ast.FunctionDef) and n.name == "make_audio")
    src_lines = text.splitlines(keepends=True)
    replacement = (
        "def make_audio(text, ident, profile=None):\n"
        "    \"\"\"Use the same native Nova DJ cache with Webbie's voice engine.\"\"\"\n"
        "    return synthesize(text, ident, profile=profile, cache=CACHE)\n"
    )
    text = "".join(src_lines[:func.lineno-1]) + replacement + "".join(src_lines[func.end_lineno:])
    text = replace_once(
        text,
        """        self.send_json_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):""",
        """        if self.path == "/dj/voices":
            self.send_json_headers(200)
            self.wfile.write(json.dumps(available_profiles()).encode())
            return
        self.send_json_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):""",
        "voice availability route",
    )
    text = replace_once(
        text,
        "            audio = make_audio(script, ident)\n",
        """            context = body.get("context") if isinstance(body.get("context"), dict) else {}
            profile = normalize_voice(context.get("voiceProfile", configured_voice()))
            audio = make_audio(script, ident, profile=profile)
""",
        "request-specific voice selection",
    )
    patched = text.encode("utf-8")
    ast.parse(patched.decode(), filename=NAME)
    after = methods(patched)
    allowed = {"make_audio", "Handler.do_GET", "Handler.do_POST"}
    for name, old_body in old.items():
        if name not in after or (name not in allowed and after[name] != old_body):
            raise ValueError("Unapproved native Nova behavior modified: " + name)
    # Only additions to known import and three reviewed method/function bodies
    # are possible. Do not load either source as an executable Python module.
    return patched


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner-archive", type=Path, required=True)
    p.add_argument("--installed-root", type=Path, default=Path("/usr/local/lib/spider-os"))
    p.add_argument("--candidate-source", type=Path,
                   default=Path(__file__).resolve().parents[1])
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        owner = load_owner_zip(a.owner_archive.expanduser().resolve())[NAME]
        root = a.installed_root.expanduser().resolve()
        if checked_path(root,NAME).read_bytes() != owner:
            raise ValueError("Installed Nova changed since owner snapshot")
        candidate = a.candidate_source.expanduser().resolve()
        if (a.output.expanduser().absolute() == root or
                root in a.output.expanduser().absolute().parents or
                candidate in a.output.expanduser().absolute().parents or
                a.output.exists() or a.output.is_symlink()):
            raise ValueError("Proposed file must be new and outside live/candidate trees")
        module = checked_path(candidate,VOICE_HELPER).read_bytes()
        patched = propose(owner, module)
        output = a.output.expanduser().absolute()
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(patched)
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    except (OSError,ValueError,SyntaxError,UnicodeError) as error:
        print("NOVA OWNER CODE MERGE BLOCKED:",type(error).__name__,str(error)[:230],
              file=sys.stderr)
        return 3
    print("PROPOSED native Nova service created:",output)
    print("Preserved owner health, DJ timing, model, host and all other methods.")
    print("NO INSTALL: Native DJ service, Media Center UI and BCN site untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
