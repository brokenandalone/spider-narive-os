"""Nova's native service patch must preserve owner DJ handling and be review-only."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "native_nova_owner_patch", ROOT/"tools/patch_owner_nova_voices.py"
)
patcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


SOURCE='''#!/usr/bin/env python3
import json, os, re, shutil, subprocess, time, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from nova_host import NovaHost, HOST as ON_AIR_HOST, STATION as STATION_NAME

MODEL = "qwen3:1.7b"
HOST = "127.0.0.1"
PORT = 9876

def ollama_script(body):
    return "owner"

def make_audio(text, ident):
    edge = Path("/opt/spider-webbie/bin/edge-tts")
    return edge

class Handler(BaseHTTPRequestHandler):
    def send_json_headers(self, status=200):
        return status

    def do_GET(self):
        if self.path == "/health":
            self.send_json_headers(200)
            self.wfile.write(b'{"ok":true}')
            return
        self.send_json_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        body = {"context": {}}
        script = ollama_script(body)
        ident = "owner"
        audio = make_audio(script, ident)
        response = {"audioFile": str(audio)}
        self.send_json_headers(200)
        self.wfile.write(json.dumps(response).encode("utf-8"))

def main():
    return "owner remains"
'''


class NovaOwnerPatchTests(unittest.TestCase):
    def sample(self):
        data=SOURCE.encode()
        helper=b'"""fixture local voice module"""\n'
        return data,helper,hashlib.sha256(data).hexdigest(),hashlib.sha1(
            ("blob "+str(len(helper))+"\\0").encode()+helper
        ).hexdigest()

    def test_only_expected_native_service_methods_change(self):
        source,helper,pin,hpin=self.sample()
        result=patcher.propose(source,helper,pin=pin,helper_pin=hpin).decode()
        self.assertIn('MODEL = "qwen3:1.7b"',result)
        self.assertIn('return "owner remains"',result)
        self.assertIn('return "owner"',result)
        self.assertIn('"/dj/voices"',result)
        self.assertIn('context.get("voiceProfile"',result)
        self.assertIn('from nova_voice import synthesize',result)
        self.assertIn('synthesize(text, ident, profile=profile, cache=CACHE)',result)
        self.assertEqual(patcher.methods(source)["main"],
                         patcher.methods(result.encode())["main"])
        self.assertEqual(patcher.methods(source)["ollama_script"],
                         patcher.methods(result.encode())["ollama_script"])

    def test_wrong_owner_source_is_denied(self):
        source,helper,pin,hpin=self.sample()
        with self.assertRaisesRegex(ValueError,"changed"):
            patcher.propose(source+b" ",helper,pin=pin,helper_pin=hpin)

    def test_wrong_voice_helper_is_denied(self):
        source,helper,pin,hpin=self.sample()
        with self.assertRaisesRegex(ValueError,"voice helper"):
            patcher.propose(source,helper+b"tamper",pin=pin,helper_pin=hpin)

    def test_missing_voice_request_marker_is_denied(self):
        source,helper,pin,hpin=self.sample()
        modified=source.replace(b"audio = make_audio(script, ident)",b"audio = None")
        with self.assertRaisesRegex(ValueError,"voice selection"):
            patcher.propose(modified,helper,
                            pin=hashlib.sha256(modified).hexdigest(),helper_pin=hpin)


if __name__=="__main__":
    unittest.main()
