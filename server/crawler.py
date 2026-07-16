"""Small Wikipedia client used by the game server.

The module intentionally keeps network access and path generation separate from
Flask so the core behavior is easy to test and reuse.
"""

from __future__ import annotations

from urllib.parse import quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    # Requests will fall back to its bundled CA certificates.
    pass

API_URL = "https://en.wikipedia.org/w/api.php"
ARTICLE_URL = "https://en.wikipedia.org/wiki/{title}"
REQUEST_TIMEOUT = 12
USER_AGENT = "WikiGame/1.0 (https://github.com/tengyuchen07-alt/wikigame)"
PUZZLE_DEPTH = 5

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


class WikipediaError(RuntimeError):
    """Raised when Wikipedia cannot provide usable data."""


def make_url(title: str) -> str:
    encoded_title = quote(title.replace(" ", "_"), safe="()")
    return ARTICLE_URL.format(title=encoded_title)


def title_from_url(url: str) -> str:
    path = urlparse(url).path
    marker = "/wiki/"
    if marker not in path:
        raise ValueError(f"Not a Wikipedia article URL: {url}")
    return unquote(path.split(marker, 1)[1]).replace("_", " ")


def _api_get(**params: object) -> dict:
    response = session.get(
        API_URL,
        params={"format": "json", "formatversion": 2, **params},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_links(title: str, limit: int = 100) -> list[str]:
    """Return unique article links from the main namespace."""
    links: list[str] = []
    continuation: dict[str, object] = {}

    while len(links) < limit:
        data = _api_get(
            action="query",
            prop="links",
            titles=title,
            plnamespace=0,
            pllimit="max",
            **continuation,
        )
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return []

        for item in pages[0].get("links", []):
            linked_title = item.get("title")
            if linked_title and linked_title not in links:
                links.append(linked_title)
                if len(links) >= limit:
                    break

        continuation = data.get("continue", {})
        if not continuation:
            break

    return links


def fetch_article_html(title: str) -> str:
    """Fetch an article and return a safe, game-focused HTML fragment."""
    response = session.get(make_url(title), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    content = soup.select_one("#mw-content-text .mw-parser-output")
    if content is None:
        raise WikipediaError(f"Article content was not found for {title!r}")

    for element in content.select(
        "script, style, table, sup, form, input, button, .navbox, .reflist, "
        ".metadata, .mw-editsection, .shortdescription, .hatnote"
    ):
        element.decompose()

    allowed_attributes = {"a": {"href", "title"}, "img": {"src", "alt"}}
    for tag in content.find_all(True):
        tag.attrs = {
            name: value
            for name, value in tag.attrs.items()
            if name in allowed_attributes.get(tag.name, set())
        }

        if tag.name == "a":
            href = tag.get("href", "")
            parsed = urlparse(href)
            is_wikipedia_host = not parsed.netloc or parsed.netloc == "en.wikipedia.org"
            is_article_path = parsed.path.startswith("/wiki/")
            article_title = unquote(parsed.path.removeprefix("/wiki/"))

            if not is_wikipedia_host or not is_article_path or ":" in article_title:
                tag.unwrap()
            else:
                # Normalize absolute Wikipedia URLs so the browser game can
                # intercept every playable article link consistently.
                tag["href"] = parsed.path
        elif tag.name == "img":
            src = tag.get("src", "")
            if src.startswith("//"):
                tag["src"] = f"https:{src}"
            elif src.startswith("/"):
                tag["src"] = f"https://en.wikipedia.org{src}"

    return str(content)


def fetch_article_text(title: str, limit: int = 4000) -> str:
    """Return readable article text for hint generation."""
    soup = BeautifulSoup(fetch_article_html(title), "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text[:limit]
