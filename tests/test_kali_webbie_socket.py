"""Kali Bay Webbie chat reuses an existing per-user Unix socket, never AI spawn."""
import importlib.util
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "kali-bay/ui/kali_bay.py"
SPEC = importlib.util.spec_from_file_location("spider_kali_webbie_ui", SOURCE)
ui = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ui)


class WebbieResidentSocketTests(unittest.TestCase):
    def test_existing_socket_exchanges_text_without_new_service(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "webbie.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(path))
                server.listen(1)
                captured = []
                errors = []

                def respond():
                    with server.accept()[0] as conn:
                        captured.append(conn.recv(8192).decode("utf-8"))
                        conn.sendall(b"Kali assistance available.")

                server.settimeout(5)
                thread = threading.Thread(target=respond, daemon=True)
                thread.start()
                worker = ui.KaliWebbieReplyWorker(
                    "[User request]\ncheck Kali Bay status", path
                )
                worker.received.connect(errors.append)
                worker.failed.connect(lambda problem: errors.append("ERROR: " + problem))
                worker.run()  # Tests fixed socket transport without QThread startup.
                thread.join(timeout=5)
                self.assertEqual(errors, ["Kali assistance available."])
                self.assertEqual(captured, ["[User request]\ncheck Kali Bay status"])

    def test_missing_socket_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.sock"
            worker = ui.KaliWebbieReplyWorker("hello", path)
            errors = []
            worker.failed.connect(errors.append)
            worker.run()
            self.assertTrue(errors)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
