#!/usr/bin/env python3
import json, os, re, shutil, subprocess, sys, time, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Also work when test harnesses load this source directly by file path.
# Keep the one Nova host module alongside the service, never in cloud packages.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nova_host import NovaHost, HOST as ON_AIR_HOST, STATION as STATION_NAME

HOST = "127.0.0.1"
PORT = 9876
MODEL = "qwen3:1.7b"
OLLAMA = "http://127.0.0.1:11434/api/chat"
VOICE = "en-AU-NatashaNeural"
CACHE = Path.home() / ".cache" / "spider-os" / "ai-dj"
CACHE.mkdir(parents=True, exist_ok=True)

PERSONA = NovaHost()


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


def make_audio(text, ident):
    edge = Path("/opt/spider-webbie/bin/edge-tts")
    mp3 = CACHE / f"{ident}.mp3"
    wav = CACHE / f"{ident}.wav"
    if edge.exists():
        try:
            subprocess.run(
                [str(edge), "--voice", VOICE, "--text", text, "--write-media", str(mp3)],
                check=True,
                timeout=22,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if mp3.exists() and mp3.stat().st_size:
                return mp3
        except Exception:
            pass
    espeak = shutil.which("espeak-ng")
    if espeak:
        try:
            subprocess.run([espeak, "-v", "en-au+f3", "-s", "165", "-w", str(wav), text], check=True, timeout=10)
            if wav.exists() and wav.stat().st_size:
                return wav
        except Exception:
            pass
    raise RuntimeError("No working TTS engine is available")


def cleanup():
    cutoff = time.time() - 86400
    for path in CACHE.glob("*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def log_message(self, fmt, *args):
        return

    def do_OPTIONS(self):
        self.headers(204)

    def do_GET(self):
        if self.path == "/health":
            self.headers(200)
            self.wfile.write(json.dumps({"ok": True, "service": "Spider AI DJ", "host": ON_AIR_HOST, "station": STATION_NAME, "port": PORT}).encode())
            return
        self.headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/dj/prepare":
            self.headers(404)
            self.wfile.write(b'{"error":"not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 24 * 1024:
                self.headers(413)
                self.wfile.write(b'{"error":"Invalid Nova request size"}')
                return
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeError):
                self.headers(400)
                self.wfile.write(b'{"error":"Invalid JSON request"}')
                return
            if not isinstance(body, dict):
                self.headers(400)
                self.wfile.write(b'{"error":"Nova expects a JSON object"}')
                return
            script = ollama_script(body)
            ident = f"dj-{int(time.time())}-{uuid.uuid4().hex[:8]}"
            audio = make_audio(script, ident)
            cleanup()
            remaining = max(0.0, min(180.0, float(body.get("secondsRemaining") or 0)))
            response = {
                "id": ident,
                "type": body.get("type") or "transition",
                "host": ON_AIR_HOST,
                "station": STATION_NAME,
                "script": script,
                "audioFile": audio.resolve().as_uri(),
                "talkOver": {
                    "startSecondsBeforeEnd": min(9.0, max(3.0, remaining - 1)) if remaining else 6.0,
                    "duckLevel": 0.28,
                    "crossfadeSeconds": 3.0,
                },
            }
            self.headers(200)
            self.wfile.write(json.dumps(response).encode("utf-8"))
        except Exception as error:
            self.headers(500)
            self.wfile.write(json.dumps({"error": str(error)}).encode("utf-8"))


def main():
    cleanup()
    print(f"{ON_AIR_HOST} for {STATION_NAME} listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
