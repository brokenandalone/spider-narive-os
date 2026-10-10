"""Nova's BCN on-air persona, used by the ONE native spider-ai-dj service."""
from collections import deque
from datetime import datetime
import random
import re
import threading

STATION = "Broken City Network"
SHORT_NAME = "BCN"
HOST = "Nova"
MAX_WORDS = 48
VALID_TYPES = {"transition", "station_id", "liner", "show_intro", "show_outro", "request"}


def clean(value, limit=160):
    if isinstance(value, (dict, list, tuple)):
        return ""
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def track_info(value):
    if not isinstance(value, dict):
        value = {}
    artist = value.get("artist") or value.get("artists") or value.get("albumArtist") or ""
    if isinstance(artist, (list, tuple)):
        artist = ", ".join(clean(item, 60) for item in artist[:4])
    return {
        "title": clean(value.get("title") or value.get("name") or value.get("track"), 100),
        "artist": clean(artist, 90),
    }


def track_phrase(track):
    title = track["title"]
    artist = track["artist"]
    return f"{title} by {artist}" if title and artist else title


def normalize_request(payload):
    """Only explicitly approved listener requests are read on air."""
    body = payload if isinstance(payload, dict) else {}
    context = body.get("context") if isinstance(body.get("context"), dict) else {}
    request = body.get("request") if isinstance(body.get("request"), dict) else {}
    mode = clean(body.get("type") or "transition", 30).lower()
    if mode not in VALID_TYPES:
        mode = "transition"
    return {
        "type": mode,
        "current": track_info(body.get("currentTrack")),
        "next": track_info(body.get("nextTrack")),
        "show": clean(context.get("showName"), 80),
        "segment": clean(context.get("segment"), 80),
        "tone": clean(context.get("tone"), 48),
        "approved_request": clean(request.get("approvedRequest"), 180) if request.get("approved") is True else "",
    }


def trim_script(text, max_words=MAX_WORDS):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.I | re.S)
    text = re.sub(r"(?m)^\s*(?:DJ|Nova|Announcer|Script|Radio)\s*:\s*", "", text)
    text = re.sub(r"\[[^\]]{0,140}\]|\([Ss]fx[^)]*\)", "", text)
    text = clean(text.replace("**", "").replace(chr(96), ""), 750)
    text = re.sub(r"\bWebbie\b", HOST, text, flags=re.I)
    if not text:
        return ""
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(",;:-") + "."
    return text


class NovaHost:
    def __init__(self, rng=None):
        self._rng = rng or random.Random()
        self._lock = threading.Lock()
        self._recent = deque(maxlen=12)

    def recent(self):
        with self._lock:
            return list(self._recent)

    def remember(self, script):
        if script:
            with self._lock:
                self._recent.append(script)

    def prompt_messages(self, payload):
        info = normalize_request(payload)
        recent = self.recent()[-6:]
        system = (
            f"You are {HOST}, the live on-air radio DJ for {STATION} ({SHORT_NAME}). "
            "You are Webbie's radio persona, but on air you always introduce yourself as Nova. "
            "Write ONLY a natural spoken on-air break of 12 to 48 words, no stage directions. "
            "Be warm, vivid and conversational. Do not sound like a list of metadata. "
            "Back-announce and tease the next song if appropriate, and vary your phrasing. "
            "Do not mention being AI or claim personal experiences. "
            "Never invent facts about artists or fabricate news, weather, sports, caller names, "
            "listener requests, traffic, events, station sponsors or broadcast availability. "
            "Only mention an explicitly approved listener request if one is supplied. "
            "Use the official station identity naturally, not in every sentence."
        )
        requested = info["approved_request"] or "none"
        data = (
            f"Break type: {info['type']}\n"
            f"Station: {STATION} ({SHORT_NAME})\n"
            f"Host: {HOST}\n"
            f"Show: {info['show'] or 'unspecified'}\n"
            f"Segment: {info['segment'] or 'unspecified'}\n"
            f"Tone: {info['tone'] or 'natural'}\n"
            f"Current track: {track_phrase(info['current']) or 'unknown'}\n"
            f"Next track: {track_phrase(info['next']) or 'unknown'}\n"
            f"Approved request: {requested}\n"
            f"Recently aired lines (avoid echoing): {' | '.join(recent) if recent else 'none'}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": data}]

    def fallback_script(self, payload):
        info = normalize_request(payload)
        mode = info["type"]
        ending = track_phrase(info["current"])
        upcoming = track_phrase(info["next"])
        show = info["show"]
        approved = info["approved_request"]

        if mode == "station_id":
            options = [
                f"You're listening to {STATION}. I'm {HOST}, and this is {SHORT_NAME}.",
                f"{STATION}. {SHORT_NAME} radio. I'm {HOST}, keeping the music moving.",
                f"This is {SHORT_NAME}, {STATION}. {HOST} is on the air.",
            ]
        elif mode == "show_intro":
            options = [
                f"Welcome to {show or STATION}. I'm {HOST}, here with you on {SHORT_NAME}.",
                f"{HOST} here. You're tuned to {SHORT_NAME}{f' for {show}' if show else ''}.",
            ]
        elif mode == "show_outro":
            options = [
                f"That wraps up {show or 'this set'} on {SHORT_NAME}. I'm {HOST}. Stay with us.",
                f"I'm {HOST}, signing off {show or 'this segment'}. The music continues on {SHORT_NAME}.",
            ]
        elif mode == "request" and approved:
            options = [
                f"{HOST} here on {SHORT_NAME}. We have an approved request: {approved}.",
                f"Here on {STATION}, this one's been requested: {approved}. I'm {HOST}.",
            ]
        elif mode == "liner":
            options = [
                f"A little more music, a little less noise. {STATION}. I'm {HOST}.",
                f"Stay with {SHORT_NAME}. I'm {HOST}, and the music keeps rolling.",
                f"You're on {STATION}, with {HOST} behind the mic.",
            ]
        else:
            back = f"That was {ending}" if ending else "That last track"
            front = f"Next up, {upcoming}" if upcoming else "More music coming up"
            options = [
                f"{back}. {HOST} here on {SHORT_NAME}. {front}.",
                f"{SHORT_NAME} radio. {back}. {front}.",
                f"I'm {HOST}, with you on {STATION}. {back}. {front}.",
                f"{back}. Coming your way on {SHORT_NAME}: {upcoming or 'more music'}.",
            ]
        recent = set(self.recent())
        unique = [option for option in options if option not in recent]
        return self._rng.choice(unique or options)

    def compose(self, payload, generate=None):
        """Use a model when available; always recover to a varied fallback."""
        script = ""
        if generate:
            try:
                script = trim_script(generate(self.prompt_messages(payload)))
            except Exception:
                script = ""
        if not script:
            script = self.fallback_script(payload)
        self.remember(script)
        return script
