from datetime import UTC, datetime
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from app.biography import folded
from app.models import Politician

WIKIPEDIA = "https://pt.wikipedia.org"
WIKIDATA = "https://www.wikidata.org"
HEADERS = {"User-Agent": "PuxandoACapivara/0.1 (public transparency project)"}


class CareerItem(BaseModel):
    title: str
    detail: str = ""
    period: str = "Período não informado"


class Career(BaseModel):
    available: bool
    professions: list[CareerItem] = Field(default_factory=list)
    previous_offices: list[CareerItem] = Field(default_factory=list)
    source_url: str = ""
    source_name: str = ""
    source_kind: str = "official"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notice: str = "Profissões e mandatos anteriores reproduzidos da fonte oficial."


class ProfessionMatch(BaseModel):
    profession: str
    people: list[Politician]
    source_url: str
    notice: str


def period(start: object, end: object) -> str:
    first, last = str(start or "").strip(), str(end or "").strip()
    if first and last:
        return f"{first}–{last}"
    return first or last or "Período não informado"


async def official_career(client: httpx.AsyncClient, person: Politician) -> Career:
    if person.provider != "camara":
        return await wikipedia_career(client, person)
    profession_response = await client.get(f"deputados/{person.id}/profissoes")
    office_response = await client.get(f"deputados/{person.id}/mandatosExternos")
    profession_response.raise_for_status()
    office_response.raise_for_status()
    professions = [
        CareerItem(title=str(item.get("titulo") or "Profissão não informada"))
        for item in profession_response.json().get("dados", [])
    ]
    offices = [
        CareerItem(
            title=str(item.get("cargo") or "Cargo não informado"),
            detail=" · ".join(
                value
                for value in (
                    str(item.get("municipio") or "").strip(),
                    str(item.get("siglaUf") or "").strip(),
                    str(item.get("siglaPartidoEleicao") or "").strip(),
                )
                if value
            ),
            period=period(item.get("anoInicio"), item.get("anoFim")),
        )
        for item in office_response.json().get("dados", [])
    ]
    result = Career(
        available=bool(professions or offices),
        professions=professions,
        previous_offices=offices,
        source_url=person.source_url,
        source_name="Câmara dos Deputados",
    )
    return result if result.available else await wikipedia_career(client, person)


def claim_ids(entity: dict[str, object], prop: str) -> list[str]:
    claims = entity.get("claims")
    if not isinstance(claims, dict):
        return []
    result: list[str] = []
    for claim in claims.get(prop, []):
        try:
            value = claim["mainsnak"]["datavalue"]["value"]["id"]
        except (KeyError, TypeError):
            continue
        if isinstance(value, str) and value not in result:
            result.append(value)
    return result


async def wikipedia_career(client: httpx.AsyncClient, person: Politician) -> Career:
    """Use structured Wikimedia data only when the official provider has no equivalent."""
    fallback = Career(
        available=False,
        notice=(
            "A fonte oficial integrada deste cargo ainda não publica profissão e cargos "
            "anteriores no mesmo formato, e não foi encontrada uma correspondência segura "
            "na Wikipédia."
        ),
    )
    try:
        search = await client.get(
            WIKIPEDIA + "/w/rest.php/v1/search/page",
            params={"q": person.name, "limit": 5},
            headers=HEADERS,
        )
        search.raise_for_status()
        candidate = next(
            (
                page
                for page in search.json().get("pages", [])
                if folded(str(page.get("title") or "")) == folded(person.name)
            ),
            None,
        )
        if candidate is None:
            return fallback
        title = str(candidate.get("title") or "")
        summary = await client.get(
            WIKIPEDIA + "/api/rest_v1/page/summary/" + quote(title, safe=""),
            headers=HEADERS,
        )
        summary.raise_for_status()
        summary_data = summary.json()
        qid = str(summary_data.get("wikibase_item") or "")
        if not qid:
            return fallback
        entity_response = await client.get(
            f"{WIKIDATA}/wiki/Special:EntityData/{qid}.json", headers=HEADERS
        )
        entity_response.raise_for_status()
        entity = entity_response.json().get("entities", {}).get(qid, {})
        profession_ids = claim_ids(entity, "P106")
        office_ids = claim_ids(entity, "P39")
        ids = profession_ids + [value for value in office_ids if value not in profession_ids]
        labels: dict[str, str] = {}
        if ids:
            label_response = await client.get(
                WIKIDATA + "/w/api.php",
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(ids),
                    "props": "labels",
                    "languages": "pt|pt-br|en",
                    "format": "json",
                },
                headers=HEADERS,
            )
            label_response.raise_for_status()
            for entity_id, value in label_response.json().get("entities", {}).items():
                published = value.get("labels", {})
                label = next(
                    (published[key]["value"] for key in ("pt", "pt-br", "en") if key in published),
                    entity_id,
                )
                labels[entity_id] = str(label)
        page_url = str(
            ((summary_data.get("content_urls") or {}).get("desktop") or {}).get("page")
            or f"{WIKIPEDIA}/wiki/{quote(title)}"
        )
        professions = [CareerItem(title=labels.get(value, value)) for value in profession_ids]
        offices = [CareerItem(title=labels.get(value, value)) for value in office_ids]
        return Career(
            available=bool(professions or offices),
            professions=professions,
            previous_offices=offices,
            source_url=page_url,
            source_name="Wikidata e Wikipédia",
            source_kind="complementary",
            notice=(
                "Informações complementares estruturadas pela comunidade Wikimedia. "
                "Consulte a fonte para conferir referências e atualizações."
            ),
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return fallback


async def people_by_profession(client: httpx.AsyncClient, profession: str) -> ProfessionMatch:
    members, professions = await __import__("asyncio").gather(
        client.get("deputados", params={"itens": 600, "ordem": "ASC", "ordenarPor": "nome"}),
        client.get(
            "https://dadosabertos.camara.leg.br/arquivos/deputadosProfissoes/json/deputadosProfissoes.json"
        ),
    )
    members.raise_for_status()
    professions.raise_for_status()
    payload = professions.json()
    published = payload.get("dados", payload) if isinstance(payload, dict) else payload
    matching_ids = {
        int(item.get("id") or str(item.get("uri", "")).rstrip("/").split("/")[-1])
        for item in published
        if str(item.get("titulo") or "").casefold() == profession.casefold()
    }
    people: list[Politician] = []
    for item in members.json().get("dados", []):
        if int(item["id"]) not in matching_ids:
            continue
        people.append(
            Politician(
                id=int(item["id"]),
                name=str(item["nome"]),
                party=str(item.get("siglaPartido") or ""),
                state=str(item.get("siglaUf") or ""),
                email=item.get("email"),
                photo_url=item.get("urlFoto"),
                source_url=str(
                    item.get("uri") or f"https://www.camara.leg.br/deputados/{item['id']}"
                ),
            )
        )
    return ProfessionMatch(
        profession=profession,
        people=people,
        source_url="https://dadosabertos.camara.leg.br/swagger/api.html",
        notice=(
            "Lista restrita aos deputados federais em exercício cuja profissão foi "
            "publicada pela Câmara com exatamente este nome."
        ),
    )
