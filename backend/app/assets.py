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

PRESIDENT_ASSET_RECORDS: dict[str, tuple[int, str] | None] = {
    "luiz inacio lula da silva": (2022, "LUIZ INACIO LULA DA SILVA"),
    "jair bolsonaro": (2022, "JAIR MESSIAS BOLSONARO"),
    "fernando collor de mello": (2022, "FERNANDO AFFONSO COLLOR DE MELLO"),
    "dilma rousseff": (2014, "DILMA VANA ROUSSEFF"),
    "michel temer": (2014, "MICHEL MIGUEL ELIAS TEMER LULIA"),
    "itamar franco": (2006, "ITAMAR AUGUSTO CAUTIERO FRANCO"),
    "fernando henrique cardoso": None,
    "jose sarney": None,
}

PRESIDENT_DIVULGA_RECORDS: dict[str, tuple[int, str, str]] = {
    "luiz inacio lula da silva": (2022, "2040602022", "280001607829"),
}


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


def _json_money(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except InvalidOperation:
        return Decimal()


async def _divulga_president_assets(
    client: httpx.AsyncClient, person: Politician, record: tuple[int, str, str]
) -> AssetDisclosure | None:
    year, election_id, candidate_id = record
    endpoint = (
        "https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/buscar/"
        f"{year}/BR/{election_id}/candidato/{candidate_id}"
    )
    try:
        response = await client.get(endpoint, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if folded(str(data.get("nomeCompleto") or "")) != folded(person.name):
        return None
    assets = [
        DeclaredAsset(
            kind=str(item.get("descricaoDeTipoDeBem") or "Tipo não informado"),
            description=str(item.get("descricao") or "Descrição não informada"),
            value=_json_money(item.get("valor")),
        )
        for item in data.get("bens", [])
        if isinstance(item, dict)
    ]
    assets.sort(key=lambda item: item.value, reverse=True)
    source = (
        "https://divulgacandcontas.tse.jus.br/divulga/#/candidato/"
        f"{year}/{election_id}/BR/{candidate_id}/bens"
    )
    return AssetDisclosure(
        available=True,
        election_year=year,
        total=sum((item.value for item in assets), Decimal()),
        assets=assets,
        source_url=source,
        notice=(
            f"Bens declarados ao TSE na candidatura de {year}, consultados individualmente "
            "no DivulgaCandContas. A declaração não comprova propriedade ou valor atuais."
        ),
    )


async def declared_assets(
    client: httpx.AsyncClient, person: Politician, year: int = 2022
) -> AssetDisclosure:
    wanted = folded(person.name)
    if person.provider == "presidentes":
        divulga_record = PRESIDENT_DIVULGA_RECORDS.get(wanted)
        if divulga_record:
            disclosure = await _divulga_president_assets(client, person, divulga_record)
            if disclosure is not None:
                return disclosure
        record = PRESIDENT_ASSET_RECORDS.get(wanted)
        if record is None:
            return AssetDisclosure(
                available=False,
                source_url="https://dadosabertos.tse.jus.br/dataset/?groups=candidatos",
                notice=(
                    "Não há declaração eleitoral em formato aberto vinculada com segurança "
                    "a este perfil presidencial. As séries de bens do TSE começam em eleições "
                    "mais recentes e só existem quando a pessoa registrou candidatura."
                ),
            )
        year, official_name = record
        wanted = folded(official_name)
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
    matches = [
        row
        for row in candidates
        if folded(row.get("NM_CANDIDATO", "")) == wanted
        and (len(person.state) != 2 or row.get("SG_UF") == person.state)
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
