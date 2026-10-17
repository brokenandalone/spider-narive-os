"""Private, content-addressed cache for repeated local manuscript reviews.

Keys include model identity, prompt text and response limit. Raw manuscript
text is never written to this cache; review observations may be sensitive.
"""
import hashlib
import os
import sqlite3
from pathlib import Path

CACHE_VERSION = "review-v1"


def cache_file():
    base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return base / "spider-os" / "author-reviews" / "review-cache.sqlite3"


def cached_review(prompt, token_limit, ask, *, path=None, model=""):
    """Cache only successfully completed Ollama responses, fail open on DB errors."""
    path = Path(path) if path is not None else cache_file()
    key = hashlib.sha256(
        (CACHE_VERSION + "\x00" + model + "\x00" + str(token_limit)
         + "\x00" + prompt).encode("utf-8")).hexdigest()
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=3)
        os.chmod(path, 0o600)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS review_cache ("
                "key TEXT PRIMARY KEY, answer TEXT NOT NULL)")
            row = connection.execute(
                "SELECT answer FROM review_cache WHERE key=?", (key,)).fetchone()
            if row is not None:
                return row[0]
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        pass

    # Slow inference happens outside the SQLite lock.
    answer = ask(prompt, token_limit)
    if answer and answer.strip():
        try:
            with sqlite3.connect(path, timeout=3) as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS review_cache ("
                    "key TEXT PRIMARY KEY, answer TEXT NOT NULL)")
                connection.execute(
                    "INSERT OR REPLACE INTO review_cache (key,answer) VALUES (?,?)",
                    (key, answer))
        except (OSError, sqlite3.Error):
            pass
    return answer
