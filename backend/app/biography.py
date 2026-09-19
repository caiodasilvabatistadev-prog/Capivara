import unicodedata
from datetime import UTC, datetime
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from app.models import Politician

WIKIPEDIA = "https://pt.wikipedia.org"
HEADERS = {"User-Agent": "PuxandoACapivara/0.1 (public transparency project)"}


class Biography(BaseModel):
    found: bool
    title: str = ""
    description: str = ""
    extract: str = ""
    source_url: str = ""
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notice: str = (
        "Texto complementar da Wikipédia, escrito e revisado pela comunidade. "
        "Não substitui a biografia oficial nem comprova fatos sem fontes adicionais."
    )


def folded(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value).casefold()
        if unicodedata.category(character) != "Mn"
    ).strip()


async def wikipedia_biography(client: httpx.AsyncClient, person: Politician) -> Biography:
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
        return Biography(found=False)
    title = str(candidate["title"])
    summary = await client.get(
        WIKIPEDIA + "/api/rest_v1/page/summary/" + quote(title, safe=""),
        headers=HEADERS,
    )
    summary.raise_for_status()
    data = summary.json()
    extract = str(data.get("extract") or "").strip()
    if not extract:
        return Biography(found=False)
    urls = data.get("content_urls") or {}
    desktop = urls.get("desktop") or {}
    return Biography(
        found=True,
        title=str(data.get("title") or title),
        description=str(data.get("description") or ""),
        extract=extract,
        source_url=str(desktop.get("page") or f"{WIKIPEDIA}/wiki/{quote(title)}"),
    )
