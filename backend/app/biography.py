import unicodedata
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from xml.etree import ElementTree as ET

import httpx
from pydantic import BaseModel, Field

from app.models import Politician
from app.news import FEED, SOURCES

WIKIPEDIA = "https://pt.wikipedia.org"
HEADERS = {"User-Agent": "PuxandoACapivara/0.1 (public transparency project)"}


class Biography(BaseModel):
    found: bool
    title: str = ""
    description: str = ""
    extract: str = ""
    source_url: str = ""
    media: list["MediaReference"] = []
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notice: str = (
        "Texto complementar da Wikipédia, escrito e revisado pela comunidade. "
        "Não substitui a biografia oficial nem comprova fatos sem fontes adicionais."
    )


class MediaReference(BaseModel):
    title: str
    publisher: str
    published_at: datetime
    source_url: str
    reference_url: str


def parse_media(content: bytes, name: str) -> list[MediaReference]:
    if len(content) > 2_000_000 or b"<!DOCTYPE" in content.upper():
        raise ValueError("Feed inválido")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError("Feed inválido") from error
    if root.tag != "rss":
        raise ValueError("Feed inválido")
    result = []
    for node in root.findall("./channel/item"):
        title = node.findtext("title", "").strip()
        source = node.find("source")
        source_url = source.get("url", "") if source is not None else ""
        publisher = next((label for domain, label in SOURCES.items() if domain in source_url), "")
        try:
            published = parsedate_to_datetime(node.findtext("pubDate", ""))
        except (TypeError, ValueError):
            continue
        if publisher and folded(name) in folded(title) and published.tzinfo is not None:
            result.append(
                MediaReference(
                    title=title,
                    publisher=publisher,
                    published_at=published,
                    source_url=source_url,
                    reference_url=node.findtext("link", ""),
                )
            )
    return sorted(result, key=lambda item: item.published_at, reverse=True)[:5]


async def media_context(client: httpx.AsyncClient, name: str) -> list[MediaReference]:
    sites = " OR ".join("site:" + domain for domain in SOURCES)
    response = await client.get(
        FEED,
        params={
            "q": f'"{name.replace(chr(34), "")}" ({sites})',
            "hl": "pt-BR",
            "gl": "BR",
            "ceid": "BR:pt-419",
        },
        headers={"Accept": "application/rss+xml"},
        timeout=20,
    )
    response.raise_for_status()
    return parse_media(response.content, name)


def folded(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value).casefold()
        if unicodedata.category(character) != "Mn"
    ).strip()


async def wikipedia_biography(client: httpx.AsyncClient, person: Politician) -> Biography:
    try:
        media = await media_context(client, person.name)
    except (httpx.HTTPError, ValueError):
        media = []
    response = await client.get(
        WIKIPEDIA + "/w/rest.php/v1/search/page",
        params={"q": person.name, "limit": 5},
        headers=HEADERS,
    )
    response.raise_for_status()
    candidate = next(
        (
            page
            for page in response.json().get("pages", [])
            if folded(str(page.get("title", ""))) == folded(person.name)
        ),
        None,
    )
    if candidate is None:
        return Biography(found=False, media=media)
    title = str(candidate["title"])
    summary = await client.get(
        WIKIPEDIA + "/api/rest_v1/page/summary/" + quote(title, safe=""),
        headers=HEADERS,
    )
    summary.raise_for_status()
    data = summary.json()
    extract = str(data.get("extract") or "").strip()
    if not extract:
        return Biography(found=False, media=media)
    urls = data.get("content_urls") or {}
    desktop = urls.get("desktop") or {}
    return Biography(
        found=True,
        title=str(data.get("title") or title),
        description=str(data.get("description") or ""),
        extract=extract,
        source_url=str(desktop.get("page") or f"{WIKIPEDIA}/wiki/{quote(title)}"),
        media=media,
    )
