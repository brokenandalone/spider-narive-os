"""Owner-scoped JARVIS STATIC website preview, bound to localhost ONLY.

This is actual local HTTP hosting, never public hosting or a deployment.
No remote binding, package execution, CGI, uploads, directory listings,
hidden/private files or arbitrary paths. STOP/owner-policy pause closes it.
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import mimetypes
import os
from pathlib import Path
import stat
import threading
from urllib.parse import unquote,urlsplit
from jarvis_local_evidence import approved_root,SKIP,SENSITIVE

ALLOWED=frozenset({
    ".html",".htm",".css",".js",".mjs",".png",".jpg",".jpeg",".gif",
    ".svg",".webp",".ico",".txt",".xml",".woff",".woff2",
    ".mp3",".ogg",".wav",
})
MAX_BYTES=40*1024*1024
HOST="127.0.0.1"


def _safe_file(root,route):
    try:
        raw=urlsplit(route)
        decoded=unquote(raw.path)
        if (raw.scheme or raw.netloc or "\0" in decoded or "\\" in decoded
                or len(decoded)>600 or not decoded.startswith("/")):
            return None
        parts=Path(decoded.lstrip("/")).parts
        if any(p in (".","..") or p.startswith(".") or
               p.casefold() in SKIP or SENSITIVE.search(p) for p in parts):
            return None
        if not parts:
            parts=("index.html",)
        candidate=root.joinpath(*parts)
        if candidate.is_dir() and not candidate.is_symlink():
            candidate=candidate/"index.html"
        current=root
        for part in candidate.relative_to(root).parts:
            current=current/part
            if current.is_symlink():
                return None
        if candidate.resolve().is_relative_to(root) is False:
            return None
        if candidate.suffix.lower() not in ALLOWED:
            return None
        info=candidate.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_size>MAX_BYTES or info.st_nlink>1):
            return None
        return candidate
    except (OSError,ValueError,PermissionError):
        return None


def _handler(root):
    class ReadOnlySite(BaseHTTPRequestHandler):
        server_version="WebbieLocalPreview/1"
        sys_version=""

        def log_message(self,fmt,*args):
            # Never persist local path, cookie, query string or browser IP.
            return

        def _respond(self,with_body):
            host=self.headers.get("Host","")
            if host not in (f"127.0.0.1:{self.server.server_port}",
                            f"localhost:{self.server.server_port}"):
                self.send_error(403,"Local preview only")
                return
            file=_safe_file(root,self.path)
            if file is None:
                self.send_error(404,"Not a public static asset")
                return
            try:
                with open(file,"rb") as input_file:
                    meta=os.fstat(input_file.fileno())
                    if (not stat.S_ISREG(meta.st_mode) or
                            meta.st_size>MAX_BYTES):
                        self.send_error(404)
                        return
                    self.send_response(200)
                    mimetype=mimetypes.guess_type(file.name)[0] or \
                        "application/octet-stream"
                    self.send_header("Content-Type",mimetype)
                    self.send_header("Content-Length",str(meta.st_size))
                    self.send_header("X-Content-Type-Options","nosniff")
                    self.send_header("Cache-Control","no-store")
                    self.send_header("Referrer-Policy","no-referrer")
                    self.send_header("X-Frame-Options","DENY")
                    self.end_headers()
                    if with_body:
                        while True:
                            data=input_file.read(65536)
                            if not data:
                                break
                            self.wfile.write(data)
            except (OSError,BrokenPipeError,ConnectionError):
                return

        def do_GET(self):
            self._respond(True)

        def do_HEAD(self):
            self._respond(False)

        def do_POST(self):
            self.send_error(405,"Local preview is read only")

        def do_PUT(self):
            self.send_error(405,"Local preview is read only")

        def do_DELETE(self):
            self.send_error(405,"Local preview is read only")

    return ReadOnlySite


class LocalSitePreview:
    def __init__(self):
        self._lock=threading.RLock()
        self._server=None
        self._thread=None
        self._folder=None

    def start(self,folder,*,home=None):
        root=approved_root(folder,home=home)
        if not any((root/name).is_file() for name in ("index.html","index.htm")):
            raise ValueError("Website preview requires a root index.html or index.htm")
        with self._lock:
            self.stop()
            server=ThreadingHTTPServer((HOST,0),_handler(root))
            server.daemon_threads=True
            thread=threading.Thread(
                target=server.serve_forever,name="webbie-static-local-preview",
                daemon=True)
            self._server=server
            self._folder=root.name
            self._thread=thread
            thread.start()
            return self.status()

    def stop(self):
        with self._lock:
            server=self._server
            thread=self._thread
            self._server=None
            self._thread=None
            self._folder=None
            if server is not None:
                server.shutdown()
                server.server_close()
            if thread is not None and thread.is_alive():
                thread.join(timeout=3)

    def status(self):
        with self._lock:
            if self._server is None:
                return {"running":False,"url":"","scope":""}
            return {
                "running":True,
                "url":f"http://{HOST}:{self._server.server_port}/",
                "scope":self._folder,
                "loopback_only":True,
                "read_only":True,
            }
