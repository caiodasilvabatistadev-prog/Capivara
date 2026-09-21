import asyncio

import httpx
from pydantic import BaseModel

from app.directories import folded
from app.models import Politician
from app.providers import Provider

SOURCE_NAMES = {
    "camara": "Câmara dos Deputados",
    "senado": "Senado Federal",
    "executivo": "Ministérios",
    "judiciario": "STJ",
    "governadores": "Governadores — 27 UFs",
    "municipais": "Prefeitos e vereadores eleitos — municípios",
    "stf": "Ministros do STF",
    "presidentes": "Ex-presidentes da República",
    "camara_historica": "Câmara — acervo histórico",
    "tse2026": "Candidaturas TSE 2026",
    "tse2024": "Candidaturas TSE 2024",
    "partidos": "Direções partidárias — TSE",
}


class SearchSource(BaseModel):
    provider: str
    name: str
    available: bool
    matches: int


class SearchResult(BaseModel):
    items: list[Politician]
    sources: list[SearchSource]


async def universal_search(
    providers: dict[str, Provider], name: str, limit: int | None = None
) -> SearchResult:
    async def consult(key: str) -> tuple[list[Politician], SearchSource]:
        try:
            items = await providers[key].search(name)
            return items, SearchSource(
                provider=key, name=SOURCE_NAMES[key], available=True, matches=len(items)
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return [], SearchSource(
                provider=key, name=SOURCE_NAMES[key], available=False, matches=0
            )

    batches = await asyncio.gather(*(consult(key) for key in SOURCE_NAMES))
    items = {(person.provider, person.id): person for batch, _ in batches for person in batch}
    ordered = sorted(
        items.values(),
        key=lambda person: (
            folded(person.name) != folded(name),
            folded(person.name),
            person.provider,
            person.id,
        ),
    )
    return SearchResult(items=ordered[:limit], sources=[source for _, source in batches])
