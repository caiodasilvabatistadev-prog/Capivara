import asyncio
import csv
from decimal import Decimal, InvalidOperation
from io import BytesIO, TextIOWrapper
from zipfile import BadZipFile, ZipFile

import httpx
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.directories import folded
from app.models import Politician


class DeclaredAsset(BaseModel):
    kind: str
    description: str
    value: Decimal
    company_url: str | None = None


class AssetDisclosure(BaseModel):
    available: bool
    election_year: int | None = None
    total: Decimal = Decimal()
    assets: list[DeclaredAsset] = Field(default_factory=list)
    source_url: str
    notice: str


def _rows(content: bytes) -> list[dict[str, str]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            result: list[dict[str, str]] = []
            for name in archive.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                with archive.open(name) as stream, TextIOWrapper(stream, encoding="cp1252") as text:
                    result.extend(csv.DictReader(text, delimiter=";"))
            return result
    except BadZipFile as error:
        raise ValueError("Arquivo eleitoral inválido") from error


def _money(value: str) -> Decimal:
    try:
        return Decimal((value or "0").replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal()


async def declared_assets(
    client: httpx.AsyncClient, person: Politician, year: int = 2022
) -> AssetDisclosure:
    if person.provider.startswith("tse"):
        year = int(person.provider.removeprefix("tse"))
    source = f"https://dadosabertos.tse.jus.br/dataset/bens-de-candidatos-{year}"
    candidates_url = (
        f"https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{year}.zip"
    )
    assets_url = (
        f"https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_{year}.zip"
    )
    try:
        candidate_response, asset_response = await asyncio.gather(
            client.get(candidates_url, timeout=60), client.get(assets_url, timeout=60)
        )
        candidate_response.raise_for_status()
        asset_response.raise_for_status()
    except httpx.HTTPError:
        return AssetDisclosure(
            available=False,
            election_year=year,
            source_url=source,
            notice=(
                f"A declaração de bens de {year} não pôde ser consultada agora. "
                "A fonte oficial do TSE está identificada abaixo; tente novamente mais tarde."
            ),
        )
    candidates, asset_rows = await asyncio.gather(
        run_in_threadpool(_rows, candidate_response.content),
        run_in_threadpool(_rows, asset_response.content),
    )
    wanted = folded(person.name)
    matches = [
        row
        for row in candidates
        if folded(row.get("NM_CANDIDATO", "")) == wanted
        and (not person.state or row.get("SG_UF") == person.state)
    ]
    if person.provider.startswith("tse"):
        matches = [row for row in candidates if row.get("SQ_CANDIDATO") == str(person.id)]
    identities = {row.get("SQ_CANDIDATO") for row in matches}
    assets = [
        DeclaredAsset(
            kind=row.get("DS_TIPO_BEM_CANDIDATO") or "Tipo não informado",
            description=row.get("DS_BEM_CANDIDATO") or "Descrição não informada",
            value=_money(row.get("VR_BEM_CANDIDATO", "0")),
        )
        for row in asset_rows
        if row.get("SQ_CANDIDATO") in identities
    ]
    assets.sort(key=lambda item: item.value, reverse=True)
    return AssetDisclosure(
        available=bool(matches),
        election_year=year,
        total=sum((item.value for item in assets), Decimal()),
        assets=assets,
        source_url=source,
        notice=(
            f"Bens declarados ao TSE na candidatura de {year}. A declaração não comprova "
            "propriedade ou valor atuais. Sites de empresas só são vinculados quando o "
            "endereço oficial pode ser confirmado; nenhum endereço é inferido pelo nome."
        ),
    )
