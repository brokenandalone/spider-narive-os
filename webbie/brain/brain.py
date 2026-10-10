#!/usr/bin/env python3
from pathlib import Path

import json
import os
import re
import sqlite3
import tempfile
import threading
import urllib.error
import urllib.request


DEFAULT_MODEL = "qwen3:1.7b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


CONFIG_FILE = Path(__file__).resolve().parents[1] / 'config/default.json'


def preferred_model(path=CONFIG_FILE):
    """Use the owner's local Ollama model choice; do not pull new models."""
    try:
        config = json.loads(Path(path).read_text(encoding='utf-8'))
        name = config.get('ollama', {}).get('model')
        if isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}', name):
            return name
    except (OSError, UnicodeError, ValueError, AttributeError, TypeError):
        pass
    return DEFAULT_MODEL


SYSTEM_PROMPT = """
You are Webbie, the resident AI built into Spider OS.

You are part of the operating system, not a website.

Your primary user is Cory.

Use the name:
- Cory normally.
- Justin inside Studio.
- Spider inside Kali Bay.
- Writer inside Author Bay.
- Student inside School/Study.

Be concise when responding by voice.
Be more detailed when responding in the graphical interface.

You help operate Spider OS, organize information, work with Forage and
Deep Forage, launch workspaces, support study and creative work, and
assist with normal computer tasks.

Never claim an action succeeded unless Spider OS actually performed it.
""".strip()


CONVERSATION_FILE = (
    Path.home()
    / ".local"
    / "state"
    / "spider-os"
    / "webbie-conversation.json"
)

MAX_CONVERSATION_MESSAGES = 16
_conversation_lock = threading.RLock()


def load_conversation():
    try:
        data = json.loads(
            CONVERSATION_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, list):
            return []

        clean = []

        for item in data:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = str(
                item.get("content", "")
            ).strip()

            if (
                role in {"user", "assistant"}
                and content
            ):
                clean.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

        return clean[
            -MAX_CONVERSATION_MESSAGES:
        ]

    except Exception:
        return []


def save_conversation(messages):
    temp = None
    try:
        CONVERSATION_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        messages = messages[
            -MAX_CONVERSATION_MESSAGES:
        ]

        with _conversation_lock:
            fd, name = tempfile.mkstemp(prefix='.webbie-conversation-',
                                        dir=CONVERSATION_FILE.parent)
            temp = Path(name)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(messages, stream, indent=2, ensure_ascii=False)
            temp.replace(CONVERSATION_FILE)

    except Exception:
        pass
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def remember_turn(user_text, assistant_text):
    user_text = str(
        user_text or ""
    ).strip()

    assistant_text = str(
        assistant_text or ""
    ).strip()

    if not user_text or not assistant_text:
        return

    with _conversation_lock:
        messages = load_conversation()
        messages.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ])

        save_conversation(messages)


def clear_conversation():
    save_conversation([])



LONG_TERM_MEMORY_DB = Path(
    "/var/lib/spider-os/webbie-brain/memory/webbie-memory.db"
)

MEMORY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but",
    "by", "for", "from", "had", "has", "have", "he",
    "her", "his", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "our", "she", "that", "the",
    "their", "them", "they", "this", "to", "was", "we",
    "were", "what", "when", "where", "which", "who",
    "will", "with", "you", "your",
}


def _memory_conn():
    conn = sqlite3.connect(
        str(LONG_TERM_MEMORY_DB),
        timeout=5,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            category TEXT NOT NULL
                DEFAULT 'general',
            content TEXT NOT NULL UNIQUE
        )
        """
    )

    conn.commit()
    return conn


def remember_memory(content, category="general"):
    content = str(content or "").strip()

    if not content:
        return False

    try:
        conn = _memory_conn()

        conn.execute(
            """
            INSERT OR IGNORE INTO memories
                (category, content)
            VALUES (?, ?)
            """,
            (
                str(category or "general"),
                content,
            ),
        )

        conn.commit()
        conn.close()

        return True

    except Exception:
        return False


def _memory_tokens(text):
    words = re.findall(
        r"[a-z0-9']+",
        str(text or "").lower(),
    )

    return {
        word
        for word in words
        if (
            len(word) > 1
            and word not in MEMORY_STOPWORDS
        )
    }


def recall_memories(query, limit=6):
    query_tokens = _memory_tokens(query)

    if not query_tokens:
        return []

    try:
        conn = _memory_conn()

        rows = conn.execute(
            """
            SELECT
                id,
                category,
                content
            FROM memories
            ORDER BY id DESC
            LIMIT 500
            """
        ).fetchall()

        conn.close()

    except Exception:
        return []

    scored = []

    for memory_id, category, content in rows:
        memory_tokens = _memory_tokens(content)

        overlap = query_tokens & memory_tokens

        if not overlap:
            continue

        score = len(overlap)

        query_lower = str(query).lower()
        content_lower = str(content).lower()

        if (
            query_lower in content_lower
            or content_lower in query_lower
        ):
            score += 3

        scored.append(
            (
                score,
                memory_id,
                category,
                content,
            )
        )

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    return [
        {
            "category": category,
            "content": content,
        }
        for _, _, category, content
        in scored[:limit]
    ]


def recent_memories(limit=10):
    try:
        conn = _memory_conn()

        rows = conn.execute(
            """
            SELECT
                category,
                content
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

        conn.close()

        return [
            {
                "category": category,
                "content": content,
            }
            for category, content in rows
        ]

    except Exception:
        return []



AUTO_MEMORY_BLOCKED_TERMS = {
    "password",
    "passphrase",
    "api key",
    "secret key",
    "access token",
    "refresh token",
    "private key",
    "credit card",
    "bank account",
    "routing number",
    "pin number",
}

AUTO_MEMORY_PATTERNS = (
    r"\bfrom now on\b",
    r"\bi prefer\b",
    r"\bwe use\b",
    r"\bwe are using\b",
    r"\bwe're using\b",
    r"\bshould use\b",
    r"\bbelongs in\b",
    r"\bgoes in\b",
    r"\bis called\b",
    r"\bis named\b",
    r"\buses version\b",
    r"\bdonor codebase\b",
    r"\bthe default\b",
)


def auto_memory_category(text):
    lower = str(text or "").lower()

    if any(x in lower for x in (
        "study", "school", "course",
        "psychology", "sociology", "snhu",
    )):
        return "study"

    if any(x in lower for x in (
        "book", "novel", "manuscript",
        "broken city", "broken world",
        "author workspace", "lore",
    )):
        return "author"

    if any(x in lower for x in (
        "studio", "song", "music",
        "recording", "audio", "vocal",
    )):
        return "studio"

    if any(x in lower for x in (
        "media center", "movie",
        "live tv", "radio",
    )):
        return "media"

    if any(x in lower for x in (
        "spider os", "webbie", "ubuntu",
        "linux", "kde", "ollama", "qwen",
    )):
        return "system"

    return "general"


def should_auto_remember(text):
    value = str(text or "").strip()

    if not value:
        return False

    if "\n" in value:
        return False

    if len(value) < 8 or len(value) > 280:
        return False

    # Automatic memory is deliberately conservative.
    # Longer spoken transcripts are much more likely to contain
    # background television, movies, or merged recognition noise.
    if len(value.split()) > 20:
        return False

    noise_phrases = (
        "you guys",
        "didn't say hi",
        "didnt say hi",
        "when i got home",
        "in the movie",
        "on the tv",
    )

    if any(
        phrase in value.lower()
        for phrase in noise_phrases
    ):
        return False

    lower = value.lower()

    if value.endswith("?"):
        return False

    if any(term in lower for term in AUTO_MEMORY_BLOCKED_TERMS):
        return False

    if any(lower.startswith(prefix) for prefix in (
        "open ",
        "launch ",
        "start ",
        "stop ",
        "close ",
        "search ",
        "research ",
        "find ",
        "look up ",
        "show ",
        "tell me ",
        "what ",
        "who ",
        "when ",
        "where ",
        "why ",
        "how ",
    )):
        return False

    return any(
        re.search(pattern, lower)
        for pattern in AUTO_MEMORY_PATTERNS
    )


def maybe_auto_remember(text):
    if not should_auto_remember(text):
        return False

    return remember_memory(
        str(text).strip(),
        category=auto_memory_category(text),
    )


def long_term_memory_response(
    message,
    context_name="Cory",
):
    text = str(message or "").strip()
    lower = text.lower()

    store_prefixes = (
        "remember that ",
        "remember this: ",
        "save this to memory: ",
        "keep this in memory: ",
    )

    for prefix in store_prefixes:
        if lower.startswith(prefix):
            content = text[len(prefix):].strip()

            if not content:
                return (
                    "Tell me what you want me "
                    "to remember."
                )

            if remember_memory(content):
                return (
                    f"I'll remember that, "
                    f"{context_name}."
                )

            return (
                "I couldn't access my long-term "
                "memory right now."
            )

    recall_prefixes = (
        "what do you remember about ",
        "do you remember anything about ",
    )

    for prefix in recall_prefixes:
        if lower.startswith(prefix):
            query = text[len(prefix):].strip()

            memories = recall_memories(
                query,
                limit=6,
            )

            if not memories:
                return (
                    "I don't have a saved long-term "
                    f"memory about {query} yet."
                )

            remembered = "; ".join(
                item["content"]
                for item in memories
            )

            return (
                f"I remember: {remembered}"
            )

    if lower in {
        "what do you remember",
        "show me your memory",
        "show me what you remember",
        "what is in your memory",
    }:
        memories = recent_memories(
            limit=8,
        )

        if not memories:
            return (
                "My long-term memory is empty."
            )

        remembered = "; ".join(
            item["content"]
            for item in memories
        )

        return (
            f"My recent long-term memories are: "
            f"{remembered}"
        )

    return None


def ask_ollama(message, context_name="Cory", model=None):
    prompt = (
        SYSTEM_PROMPT
        + "\n\nCurrent user name: "
        + context_name
    )

    relevant_memories = recall_memories(
        message,
        limit=6,
    )

    if relevant_memories:
        memory_text = "\n".join(
            "- " + item["content"]
            for item in relevant_memories
        )

        prompt += (
            "\n\nRelevant long-term memory:\n"
            + memory_text
            + "\nUse these memories only when "
            "they are relevant to the current request."
        )

    payload = {
        "model": preferred_model() if model is None else model,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "num_predict": 256,
            "temperature": 0.6,
        },
        "messages": (
            [
                {
                    "role": "system",
                    "content": prompt,
                }
            ]
            + load_conversation()
            + [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        ),
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=180,
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        return (
            data.get("message", {})
            .get("content", "")
            .strip()
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        KeyError,
    ):
        return None



RESEARCH_ROOT = Path.home() / ".local" / "share" / "webbie" / "research"
RESEARCH_LATEST = RESEARCH_ROOT / "findings" / "latest.md"
RESEARCH_SUMMARIES = RESEARCH_ROOT / "summaries"


def research_response(message):
    lower = message.lower().strip()

    research_phrases = (
        "what have you researched",
        "what did you research",
        "what are you researching",
        "what have you learned",
        "latest research",
        "your research",
        "past research",
        "previous research",
        "research history",
        "research memory",
        "remember your research",
        "remember past research",
        "do you remember your research",
        "do you remember what you researched",
    )

    if not any(phrase in lower for phrase in research_phrases):
        return None

    if not RESEARCH_LATEST.exists():
        return "I don't have a completed saved research brief yet."

    try:
        latest_text = RESEARCH_LATEST.read_text(
            encoding="utf-8",
            errors="replace",
        )

        topic = None

        for line in latest_text.splitlines():
            if line.startswith("**Topic:**"):
                topic = line.replace("**Topic:**", "", 1).strip()
                break

        topics = []

        if RESEARCH_SUMMARIES.exists():
            files = sorted(
                RESEARCH_SUMMARIES.glob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for file in files[:12]:
                try:
                    content = file.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )

                    for line in content.splitlines():
                        if line.startswith("**Topic:**"):
                            found = line.replace(
                                "**Topic:**",
                                "",
                                1,
                            ).strip()

                            if found and found not in topics:
                                topics.append(found)
                            break
                except Exception:
                    continue

        if (
            "latest research" in lower
            or "what are you researching" in lower
        ):
            if topic:
                return (
                    f"My latest completed research is about {topic}. "
                    "The full brief is saved in my research findings."
                )

        if topics:
            topic_list = "; ".join(topics[:6])

            if topic:
                return (
                    "I've researched these recent topics: "
                    f"{topic_list}. "
                    f"My latest completed research is {topic}."
                )

            return (
                "I've researched these recent topics: "
                f"{topic_list}."
            )

        if topic:
            return f"My latest completed research is about {topic}."

        return (
            "I have saved research, but I couldn't identify its topic."
        )

    except Exception as exc:
        return (
            "I found my research files, but I couldn't read them "
            f"correctly: {exc}"
        )


def built_in_response(message, context_name="Cory"):
    lower = message.lower().strip()

    if lower in {
        "hello",
        "hi",
        "hey",
    }:
        return f"Hey {context_name}. I'm here."

    if "who are you" in lower:
        return (
            "I'm Webbie, the resident AI inside Spider OS."
        )

    if "what are you" in lower:
        return (
            "I'm Webbie, the resident AI layer of Spider OS."
        )

    return (
        f"I heard you, {context_name}. "
        "My local language model is not online yet, "
        "but my Spider OS controls are available."
    )


def respond(message, context_name="Cory"):
    memory_answer = long_term_memory_response(
        message,
        context_name=context_name,
    )

    if memory_answer:
        remember_turn(
            message,
            memory_answer,
        )

        return memory_answer

    maybe_auto_remember(message)

    research_answer = research_response(message)

    if research_answer:
        remember_turn(
            message,
            research_answer,
        )

        return research_answer

    answer = ask_ollama(
        message,
        context_name=context_name,
    )

    if answer:
        remember_turn(
            message,
            answer,
        )

        return answer

    fallback = built_in_response(
        message,
        context_name=context_name,
    )

    remember_turn(
        message,
        fallback,
    )

    return fallback
