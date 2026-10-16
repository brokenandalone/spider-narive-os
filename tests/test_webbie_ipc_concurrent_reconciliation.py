#!/usr/bin/env python3
"""Socket worker proof without importing Webbie's live audio, screen or AI modules."""
import ast
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConcurrentSocketTests(unittest.TestCase):
    def test_fast_builtin_not_blocked_by_slow_ai(self):
        source = (ROOT / "webbie/agent/webbie.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "socket_server"
        )
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "webbie.sock"
            listening = threading.Event()
            release_slow = threading.Event()
            running = {"live": True}

            def handle(command, voice=False):
                self.assertFalse(voice)
                if command == "slow":
                    listening.set()
                    release_slow.wait(timeout=3)
                return "answer:" + command

            # A single AST function runs under a mocked, temporary socket path.
            namespace = {
                "socket": socket,
                "SOCKET_PATH": socket_path,
                "os": os,
                "threading": threading,
                "handle_command": handle,
                "running": True,
            }
            compiled = compile(ast.Module(body=[function], type_ignores=[]),
                               str(ROOT / "webbie/agent/webbie.py"), "exec")
            exec(compiled, namespace)
            server = threading.Thread(target=namespace["socket_server"], daemon=True)
            server.start()
            try:
                for _ in range(200):
                    if socket_path.is_socket():
                        break
                    time.sleep(0.01)
                self.assertTrue(socket_path.is_socket())

                def call(command):
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                        client.settimeout(2)
                        client.connect(str(socket_path))
                        client.sendall(command.encode())
                        return client.recv(200).decode()

                answer = []
                slow = threading.Thread(target=lambda: answer.append(call("slow")), daemon=True)
                slow.start()
                self.assertTrue(listening.wait(timeout=2))

                started = time.monotonic()
                fast = call("who are you")
                elapsed = time.monotonic() - started
                self.assertEqual(fast, "answer:who are you")
                self.assertLess(elapsed, 0.6, "a slow AI turn blocked fast socket commands")
                release_slow.set()
                slow.join(timeout=3)
                self.assertEqual(answer, ["answer:slow"])
                self.assertEqual(socket_path.stat().st_mode & 0o777, 0o600)
            finally:
                release_slow.set()
                namespace["running"] = False
                server.join(timeout=3)
            self.assertFalse(server.is_alive())


if __name__ == "__main__":
    unittest.main()
