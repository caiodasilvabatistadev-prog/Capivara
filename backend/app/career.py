from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, Field

from app.models import Politician


class CareerItem(BaseModel):
    title: str
    detail: str = ""
    period: str = "Período não informado"


class Career(BaseModel):
    available: bool
    professions: list[CareerItem] = Field(default_factory=list)
    previous_offices: list[CareerItem] = Field(default_factory=list)
    source_url: str = ""
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
        return Career(
            available=False,
            notice=(
                "A fonte oficial integrada deste cargo ainda não publica profissão "
                "e cargos anteriores no mesmo formato."
            ),
        )
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
    return Career(
        available=bool(professions or offices),
        professions=professions,
        previous_offices=offices,
        source_url=person.source_url,
    )


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
