#!/usr/bin/env python3
import json, os, re, shutil, subprocess, time, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from nova_host import NovaHost, HOST as ON_AIR_HOST, STATION as STATION_NAME
from nova_voice import synthesize, available_profiles, normalize_voice, configured_voice

HOST = "127.0.0.1"
PORT = 9876
MODEL = "qwen3:1.7b"
OLLAMA = "http://127.0.0.1:11434/api/chat"
CACHE = Path.home() / ".cache" / "spider-os" / "ai-dj"
CACHE.mkdir(parents=True, exist_ok=True)

PERSONA = NovaHost()
LAST_VOICE = {'engine': 'no-break-prepared', 'usedFallback': False}


def track_text(track):
    if not isinstance(track, dict):
        return "unknown track"
    title = track.get("title") or track.get("name") or track.get("track") or "unknown track"
    artist = track.get("artist") or track.get("artists") or track.get("albumArtist") or ""
    if isinstance(artist, list):
        artist = ", ".join(str(x) for x in artist)
    return f"{title} by {artist}" if artist else str(title)


def ollama_script(body):
    """Generate Nova's live copy with the existing model, or use the fallback."""
    def generate(messages):
        payload = {
            "model": MODEL,
            "stream": False,
            "think": False,
            "messages": messages,
            "options": {"temperature": 0.85, "top_p": 0.9}
        }
        req = urllib.request.Request(
            OLLAMA,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Always leave time for the TTS stage or a canned fallback.
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("message", {}).get("content", "")

    return PERSONA.compose(body, generate)


def make_audio(text, ident, profile=None, report=None):
    """On-air Nova must use a neural voice or stay silent, never robotic eSpeak."""
    return synthesize(text, ident, profile=profile, cache=CACHE,
                      allow_espeak=False, report=report)


def cleanup():
    cutoff = time.time() - 86400
    for path in CACHE.glob("*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def send_json_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def log_message(self, fmt, *args):
        return

    def do_OPTIONS(self):
        self.send_json_headers(204)

    def do_GET(self):
        if self.path == "/health":
            self.send_json_headers(200)
            self.wfile.write(json.dumps({"ok": True, "service": "Spider AI DJ", "host": ON_AIR_HOST, "station": STATION_NAME, "port": PORT}).encode())
            return
        if self.path == "/dj/voices":
            self.send_json_headers(200)
            self.wfile.write(json.dumps({**available_profiles(), "lastVoice": dict(LAST_VOICE),
                                          "robotVoiceAllowed": False}).encode())
            return
        self.send_json_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/dj/prepare":
            self.send_json_headers(404)
            self.wfile.write(b'{"error":"not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 24 * 1024:
                self.send_json_headers(413)
                self.wfile.write(b'{"error":"Invalid Nova request size"}')
                return
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(body, dict):
                raise ValueError("Nova expects a JSON object")
            script = ollama_script(body)
            ident = f"dj-{int(time.time())}-{uuid.uuid4().hex[:8]}"
            context = body.get("context") if isinstance(body.get("context"), dict) else {}
            profile = normalize_voice(context.get("voiceProfile", configured_voice()))
            voice_report = {}
            try:
                audio = make_audio(script, ident, profile=profile, report=voice_report)
            except Exception as error:
                LAST_VOICE.update({'engine': 'unavailable', 'error': str(error),
                                   'voiceProfileRequested': profile})
                raise
            LAST_VOICE.update(voice_report or {'engine': 'unverified'})
            LAST_VOICE.pop('error', None)
            cleanup()
            remaining = max(0.0, min(180.0, float(body.get("secondsRemaining") or 0)))
            response = {
                "id": ident,
                "type": body.get("type") or "transition",
                "host": ON_AIR_HOST,
                "station": STATION_NAME,
                "script": script,
                "audioFile": audio.resolve().as_uri(),
                "voiceEngine": voice_report.get("engine", "unverified"),
                "voiceProfileRequested": profile,
                "voiceFallback": voice_report.get("usedFallback", False),
                "talkOver": {
                    "startSecondsBeforeEnd": min(9.0, max(3.0, remaining - 1)) if remaining else 6.0,
                    "duckLevel": 0.28,
                    "crossfadeSeconds": 3.0,
                },
            }
            self.send_json_headers(200)
            self.wfile.write(json.dumps(response).encode("utf-8"))
        except Exception as error:
            self.send_json_headers(500)
            self.wfile.write(json.dumps({"error": str(error)}).encode("utf-8"))


def main():
    cleanup()
    print(f"{ON_AIR_HOST} for {STATION_NAME} listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
