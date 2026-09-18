import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx
from pydantic import BaseModel, Field

from app.directories import folded

SOURCES = {
    "g1.globo.com": "G1",
    "folha.uol.com.br": "Folha de S.Paulo",
    "estadao.com.br": "Estadão",
    "uol.com.br": "UOL",
    "cnnbrasil.com.br": "CNN Brasil",
    "poder360.com.br": "Poder360",
    "intercept.com.br": "Intercept Brasil",
}
TERMS = {
    "condenação": r"\bcondenad[oa]s?\b|\bcondenacao\b",
    "suspeita": r"\bsuspeit[oa]s?\b",
    "julgamento": r"\bjulgad[oa]s?\b|\bjulgamento\b",
    "investigação": r"\binvestigad[oa]s?\b|\binvestigacao\b",
    "apologia": r"\bapologia\b",
    "crime": r"\bcrimes?\b",
}
FEED = "https://news.google.com/rss/search"


class NewsItem(BaseModel):
    title: str
    publisher: str
    published_at: datetime
    source_url: str
    reference_url: str
    matched_terms: list[str]


class NewsResult(BaseModel):
    subject_name: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[NewsItem] = []
    notice: str = (
        "Busca automática em títulos indexados pelo Google Notícias, limitada aos veículos "
        "selecionados. Pode omitir notícias e incluir homônimos ou fatos sobre terceiros. "
        "Os termos são filtros de busca, não conclusões sobre a pessoa. "
        "Não confirma culpa, condenação, absolvição ou situação atual de processos. "
        "Não encontrar resultados não significa ausência de notícias ou processos."
    )


def parse_news(content: bytes, name: str) -> list[NewsItem]:
    if len(content) > 2_000_000 or b"<!DOCTYPE" in content.upper():
        raise ValueError("Feed inválido")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError("Feed inválido") from error
    if root.tag != "rss":
        raise ValueError("Feed inválido")
    items: list[NewsItem] = []
    seen: set[str] = set()
    for node in root.findall("./channel/item"):
        title = node.findtext("title", "").strip()
        source = node.find("source")
        source_url = source.get("url", "") if source is not None else ""
        host = urlparse(source_url).hostname or ""
        domain = next((key for key in SOURCES if host == key or host.endswith("." + key)), "")
        reference = node.findtext("link", "")
        text = folded(title)
        terms = [label for label, pattern in TERMS.items() if re.search(pattern, text)]
        if (
            not domain
            or urlparse(source_url).scheme != "https"
            or urlparse(reference).hostname != "news.google.com"
            or urlparse(reference).scheme != "https"
            or not re.search(r"\b" + re.escape(folded(name)) + r"\b", text)
            or not terms
            or text in seen
        ):
            continue
        try:
            published = parsedate_to_datetime(node.findtext("pubDate", ""))
        except (ValueError, TypeError):
            continue
        if published.tzinfo is None:
            continue
        seen.add(text)
        items.append(
            NewsItem(
                title=title,
                publisher=SOURCES[domain],
                published_at=published,
                source_url=source_url,
                reference_url=reference,
                matched_terms=terms,
            )
        )
    return sorted(items, key=lambda item: item.published_at, reverse=True)[:20]


async def search_news(client: httpx.AsyncClient, name: str) -> NewsResult:
    sites = " OR ".join("site:" + domain for domain in SOURCES)
    query = (
        '"'
        + name.replace('"', "")
        + '" (condenado OR suspeito OR julgado OR investigado OR apologia OR crime '
        + "OR condenação OR investigação OR julgamento) ("
        + sites
        + ")"
    )
    response = await client.get(
        FEED,
        params={"q": query, "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
        headers={"Accept": "application/rss+xml"},
        timeout=20,
    )
    response.raise_for_status()
    return NewsResult(subject_name=name, items=parse_news(response.content, name))
