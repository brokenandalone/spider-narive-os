"""Deterministic Jarvis-style website and search request routing.

No browsing happens here. Only direct user commands become a reviewed
proposal for the trusted desktop GUI. Model output, screen observations and
page text must never be passed to this parser as commands.
"""
from __future__ import annotations
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import quote_plus, urlsplit, urlunsplit

ALIASES = {
    "youtube": "https://www.youtube.com/",
    "github": "https://github.com/",
    "wikipedia": "https://www.wikipedia.org/",
    "google": "https://www.google.com/",
    "snhu": "https://www.snhu.edu/",
    "outlook": "https://outlook.office.com/",
    "firefox": None,  # an installed application, not a website alias
}
COMMAND = re.compile(r"^(?:please\s+)?(?:open|visit|navigate to|go to|show me)\s+(?:a\s+)?(?:(?:new\s+)?(?:web\s*page|website|web\s*site|browser\s*tab|tab|page)\s+(?:for\s+|at\s+|to\s+)?)?(?P<target>.+)$", re.I)
SEARCH = re.compile(r"^(?:please\s+)?(?:search (?:the )?web for|look up online|google|search online for)\s+(?P<query>.+)$", re.I)
PREFIX = re.compile(r"^(?:hey\s+)?(?:webbie|webby|web)[\s,.:]+", re.I)
MAX_URL = 1500


@dataclass(frozen=True)
class BrowserRequest:
    url: str
    label: str
    kind: str


def canonical_url(raw):
    """Only HTTPS addresses at public-looking DNS hostnames (no local/IP URLs)."""
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_URL:
        raise ValueError("Website address is empty or too long")
    source = raw.strip()
    if re.search(r"[\x00-\x20\x7f\\]", source):
        raise ValueError("Website address contains unsupported characters")
    if source.startswith("//") or source.startswith("#"):
        raise ValueError("Provide a normal HTTPS address")
    if "://" not in source:
        source = "https://" + source
    parsed = urlsplit(source)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("Only HTTPS websites may be opened")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Website addresses cannot embed credentials")
    host = parsed.hostname
    if host is None or len(host) > 253:
        raise ValueError("Invalid website hostname")
    host = host.rstrip(".").lower()
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        raise ValueError("Website hostname must be ordinary ASCII DNS")
    labels = host.split(".")
    if (len(labels) < 2 or any(not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", item)
            for item in labels)):
        raise ValueError("Only complete public-looking domain names are supported")
    if host.endswith((".local", ".internal", ".localhost", ".test", ".invalid", ".example")):
        raise ValueError("Local and test addresses cannot be opened this way")
    try:
        ipaddress.ip_address(host)
        raise ValueError("Direct IP addresses are not opened by this route")
    except ValueError as error:
        if str(error) == "Direct IP addresses are not opened by this route":
            raise
    if not labels[-1].isalpha() or len(labels[-1]) < 2:
        raise ValueError("Website requires a valid domain ending")
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid website port")
    if port not in (None, 443):
        raise ValueError("Nonstandard network ports need manual browser entry")
    if "@" in parsed.netloc:
        raise ValueError("Website cannot contain an @ sign")
    path = parsed.path or "/"
    if len(path) + len(parsed.query) + len(parsed.fragment) > MAX_URL:
        raise ValueError("Website path too long")
    return urlunsplit(("https", host, path, parsed.query, parsed.fragment))


def parse_browser_command(text):
    """Recognize explicit top-level user navigation or search commands."""
    if not isinstance(text, str) or not 1 <= len(text) <= 1600:
        return None
    phrase = PREFIX.sub("", text.strip(), count=1)
    match = SEARCH.fullmatch(phrase)
    if match:
        query = match.group("query").strip().rstrip(".")
        if not 1 <= len(query) <= 300:
            return None
        url = "https://www.google.com/search?q=" + quote_plus(query)
        return BrowserRequest(url, "Search web for: " + query[:100], "search")
    match = COMMAND.fullmatch(phrase)
    if not match:
        return None
    raw = match.group("target").strip().strip(" \"'")
    if raw.endswith(".") and "/" not in raw:
        raw = raw[:-1]
    target = raw.lower().replace("the ", "", 1)
    if target in ALIASES:
        if ALIASES[target] is None:
            return None
        return BrowserRequest(ALIASES[target], "Open " + target, "website")
    # Do not accidentally treat "open terminal", app names, or natural text
    # as hostnames. Browser routing happens only for recognizable addresses.
    if not ("." in raw and " " not in raw):
        return None
    try:
        url = canonical_url(raw)
    except ValueError:
        # Explicit invalid web URLs are rejected, not treated as app names.
        return BrowserRequest("", "Blocked unsupported URL", "blocked")
    return BrowserRequest(url, "Open website: " + urlsplit(url).hostname, "website")
