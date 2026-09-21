import csv
import json
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO, TextIOWrapper
from typing import cast
from zipfile import BadZipFile, ZipFile

import httpx
from pydantic import BaseModel, Field

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

# Snapshot of the official DivulgaCandContas response, last updated there on 2022-08-06.
# It keeps the public profile useful when the TSE host rejects server-to-server TLS requests.
LULA_2022_ASSETS = (
    ("VGBL - Vida Gerador de Benefício Livre", "VGBL", "5570798.99"),
    ("Terreno", "Terreno", "265000"),
    (
        "OUTROS BENS E DIREITOS",
        "Devolução de valores bloqueados por determinação judicial",
        "250722.03",
    ),
    ("Construção", "Casa em construção", "246918.82"),
    ("Crédito decorrente de empréstimo", "Crédito decorrente de empréstimo pessoal", "200000"),
    ("Aplicação de renda fixa (CDB, RDB e outros)", "CDB", "185744.81"),
    (
        "OUTROS BENS E DIREITOS",
        "Crédito decorrente de procedência de demanda judicial",
        "179298.96",
    ),
    ("Terreno", "Terreno", "130000"),
    ("Apartamento", "Apartamento", "94571.25"),
    ("Veículo automotor terrestre: caminhão, automóvel, moto, etc.", "Automóvel", "85000"),
    ("Crédito decorrente de empréstimo", "Crédito decorrente de empréstimo pessoal", "50000"),
    ("Quotas ou quinhões de capital", "Empresa", "49000"),
    ("Veículo automotor terrestre: caminhão, automóvel, moto, etc.", "Automóvel", "48475"),
    ("Apartamento", "Apartamento", "19167.34"),
    ("Apartamento", "Apartamento", "19167.34"),
    ("Depósito bancário em conta corrente no País", "Saldo em conta corrente", "18681.23"),
    ("Caderneta de poupança", "Poupança", "4719.20"),
    ("Terreno", "Terreno", "2733.45"),
    ("Depósito bancário em conta corrente no País", "Saldo em conta corrente", "2180"),
    ("Fundo de Curto Prazo", "Fundo de Curto Prazo", "1213.17"),
    ("Outras aplicações e investimentos", "Aplicação financeira", "333.17"),
    ("Depósito bancário em conta corrente no País", "Saldo em conta corrente", "1"),
    ("Caderneta de poupança", "Poupança", "0.02"),
)


class DeclaredAsset(BaseModel):
    kind: str
    description: str
    value: Decimal
    company_url: str | None = None


class AssetHistory(BaseModel):
    year: int
    total: Decimal


class AssetSourceCheck(BaseModel):
    name: str
    status: str
    url: str
    year: int | None = None
    total: Decimal | None = None
    note: str


class AssetDisclosure(BaseModel):
    available: bool
    election_year: int | None = None
    total: Decimal = Decimal()
    assets: list[DeclaredAsset] = Field(default_factory=list)
    history: list[AssetHistory] = Field(default_factory=list)
    growth_percentage: Decimal | None = None
    verification: str = "unverified"
    source_checks: list[AssetSourceCheck] = Field(default_factory=list)
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


def _hub_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", folded(name))


def _hub_value(page: str, key: str) -> object | None:
    decoded = ""
    for match in re.finditer(r"self\.__next_f\.push\((\[.*?\])\)</script>", page):
        try:
            chunk = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        if len(chunk) > 1 and isinstance(chunk[1], str):
            decoded += chunk[1]
    marker = f'"{key}":'
    position = decoded.find(marker)
    if position < 0:
        return None
    try:
        payload, _ = json.JSONDecoder().raw_decode(decoded[position + len(marker) :])
    except json.JSONDecodeError:
        return None
    return cast(object, payload)


def _hub_payload(page: str) -> dict[str, object] | None:
    payload = _hub_value(page, "bens")
    return payload if isinstance(payload, dict) else None


async def _hub_assets(
    client: httpx.AsyncClient, person: Politician, year: int
) -> AssetDisclosure | None:
    slug = _hub_slug(person.name)
    page_url = f"https://hubpolitico.com.br/perfil/{slug}/financeiro/patrimonio/{year}"
    try:
        response = await client.get(page_url, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    payload = _hub_payload(response.text)
    if not payload or payload.get("ano") != year or not payload.get("disponivel"):
        return None
    raw_assets = payload.get("bens")
    if not isinstance(raw_assets, list):
        return None
    assets = [
        DeclaredAsset(
            kind=str(item.get("tipo") or "Tipo não informado"),
            description=str(item.get("descricao") or "Descrição não informada"),
            value=_json_money(item.get("valor")),
        )
        for item in raw_assets
        if isinstance(item, dict)
    ]
    assets.sort(key=lambda item: item.value, reverse=True)
    raw_history = _hub_value(response.text, "serie")
    history = sorted(
        [
            AssetHistory(year=int(item["ano"]), total=_json_money(item.get("patrimonio_total")))
            for item in raw_history
            if isinstance(item, dict)
            and item.get("ano")
            and item.get("patrimonio_total") is not None
        ],
        key=lambda item: item.year,
    ) if isinstance(raw_history, list) else []
    growth = None
    if len(history) > 1 and history[0].total > 0:
        growth = (history[-1].total - history[0].total) * 100 / history[0].total
    return AssetDisclosure(
        available=True,
        election_year=year,
        total=sum((item.value for item in assets), Decimal()),
        assets=assets,
        history=history,
        growth_percentage=growth,
        verification="single_source",
        source_checks=[
            AssetSourceCheck(
                name="HubPolítico",
                status="found",
                url=page_url,
                year=year,
                total=sum((item.value for item in assets), Decimal()),
                note="Publicação localizada e associada ao nome e ao ano consultados.",
            )
        ],
        source_url=page_url,
        notice=(
            f"Patrimônio informado na cobertura eleitoral de {year} do HubPolítico. "
            "Os valores retratam a publicação daquela eleição e não comprovam propriedade "
            "ou valor atuais."
        ),
    )


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


def _lula_snapshot() -> AssetDisclosure:
    year, election_id, candidate_id = PRESIDENT_DIVULGA_RECORDS["luiz inacio lula da silva"]
    assets = [
        DeclaredAsset(kind=kind, description=description, value=Decimal(value))
        for kind, description, value in LULA_2022_ASSETS
    ]
    return AssetDisclosure(
        available=True,
        election_year=year,
        total=sum((item.value for item in assets), Decimal()),
        assets=assets,
        source_url=(
            "https://divulgacandcontas.tse.jus.br/divulga/#/candidato/"
            f"{year}/{election_id}/BR/{candidate_id}/bens"
        ),
        notice=(
            "Bens declarados ao TSE na candidatura de 2022. Como a consulta ao vivo está "
            "indisponível, exibimos o retrato da resposta oficial do DivulgaCandContas, "
            "atualizada em 06/08/2022. A declaração não comprova propriedade ou valor atuais."
        ),
    )


async def declared_assets(
    client: httpx.AsyncClient, person: Politician, year: int = 2022
) -> AssetDisclosure:
    if person.provider.startswith("tse"):
        year = int(person.provider.removeprefix("tse"))
    hub_disclosure = await _hub_assets(client, person, year)
    if hub_disclosure is not None:
        return hub_disclosure
    return AssetDisclosure(
        available=False,
        election_year=year,
        source_url=f"https://hubpolitico.com.br/perfil/{_hub_slug(person.name)}/financeiro/patrimonio/{year}",
        source_checks=[
            AssetSourceCheck(
                name="HubPolítico",
                status="not_found",
                url=(
                    "https://hubpolitico.com.br/perfil/"
                    f"{_hub_slug(person.name)}/financeiro/patrimonio/{year}"
                ),
                year=year,
                note="Nenhuma publicação com correspondência segura foi encontrada.",
            )
        ],
        notice=(
            "Não encontramos uma publicação alternativa de patrimônio com correspondência "
            "segura para este perfil. Nenhum valor foi preenchido a partir do TSE."
        ),
    )
