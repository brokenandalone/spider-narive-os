"""Forage's public-web search router. SearXNG stays bound to loopback."""
import ipaddress
import json
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

SEARXNG = "http://127.0.0.1:8888/search"
MAX_REPLY = 2 * 1024 * 1024


def public_url(value):
    """Conservatively exclude dangerous URLs before Deep Forage reads them."""
    if not isinstance(value, str) or len(value) > 4096:
        return False
    try:
        parts = urlsplit(value)
        host = (parts.hostname or "").lower().rstrip(".")
        if parts.scheme not in {"http", "https"} or not host or parts.username or parts.password:
            return False
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False
        if "." not in host:
            return False
        try:
            ip = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            return True
        return ip.is_global
    except (ValueError, TypeError):
        return False


def clean_results(items, limit, engine):
    results, seen = [], set()
    for item in items or ():
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("href") or "")
        if not public_url(url) or url in seen:
            continue
        seen.add(url)
        results.append({
            "title": str(item.get("title") or url)[:300],
            "url": url,
            "snippet": str(item.get("snippet") or item.get("content") or item.get("body") or "")[:3000],
            "engine": engine,
            "published": str(item.get("publishedDate") or item.get("date") or "")[:80],
        })
        if len(results) >= limit:
            break
    return results


def search_web(query, max_results=12, timelimit=None, ddgs_factory=None, opener=None):
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise ValueError("Forage needs a search query of 1 to 1000 characters.")
    if not isinstance(max_results, int) or not 1 <= max_results <= 50:
        raise ValueError("Search result limit must be between 1 and 50.")
    opener = opener or urlopen
    params = {"q": query, "format": "json", "categories": "general", "safesearch": "1"}
    if timelimit in {"d", "w", "m", "y"}:
        params["time_range"] = timelimit
    primary_error = None
    try:
        request = Request(SEARXNG + "?" + urlencode(params), headers={"User-Agent": "SpiderOS-Forage/1.0"})
        with opener(request, timeout=8) as response:
            raw = response.read(MAX_REPLY + 1)
        if len(raw) > MAX_REPLY:
            raise ValueError("SearXNG response exceeded limit")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError("Unexpected SearXNG response")
        found = clean_results(data["results"], max_results, "searxng")
        if found:
            return found
    except (OSError, TimeoutError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        primary_error = exc

    try:
        factory = ddgs_factory() if callable(ddgs_factory) else None
        if factory is None:
            if primary_error:
                raise RuntimeError("SearXNG unavailable and DDGS fallback not installed") from primary_error
            return []
        hits = factory(timeout=15).text(query, region="us-en", safesearch="moderate",
                                        timelimit=timelimit, max_results=max_results, backend="auto")
        return clean_results(hits, max_results, "ddgs")
    except Exception as exc:
        raise RuntimeError("Both Forage search providers failed. Check local SearXNG and DDGS.") from exc
