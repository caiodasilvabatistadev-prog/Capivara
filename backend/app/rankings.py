import asyncio
import csv
import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO, TextIOWrapper
from typing import Any, Literal
from zipfile import BadZipFile, ZipFile

import httpx
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.dashboard import parse_dashboard
from app.models import Politician
from app.parties import PARTIES, Party
from app.providers import Provider

MetricName = Literal[
    "expenses",
    "absences",
    "approved",
    "amendments",
    "party_fund",
    "election_fund",
]
TRANSPARENCY_API = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"


def public_money(value: object) -> Decimal:
    normalized = re.sub(r"[^0-9,.-]", "", str(value or "0"))
    return Decimal(normalized.replace(".", "").replace(",", "."))


TSE_PARTY = "https://www.tse.jus.br/comunicacao/noticias/2026/Janeiro/fundo-partidario-19-partidos-receberam-mais-de-r-1-bilhao-em-2025"
TSE_ELECTION = "https://www.tse.jus.br/eleicoes/eleicoes-2026-content/prestacao-de-contas/distribuicao-dos-recursos-do-fundo-especial-de-financiamento-de-campanha-fefc-eleicoes-2026"


class Entry(BaseModel):
    party: Party | None = None
    position: int = 0
    id: int | None = None
    name: str
    photo_url: str | None = None
    value: Decimal
    detail: str = ""


class Ranking(BaseModel):
    provider: str
    metric: MetricName
    year: int
    status: Literal["ready", "partial", "unavailable", "not_applicable"] = "unavailable"
    title: str
    unit: str = "BRL"
    notice: str
    source_url: str = ""
    source_as_of: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    covered: int = 0
    total: int | None = None
    entries: list[Entry] = []


def ordered(entries: Iterable[Entry]) -> list[Entry]:
    result = sorted(entries, key=lambda item: (-item.value, item.name.casefold()))
    previous = None
    position = 0
    for index, entry in enumerate(result):
        if entry.value != previous:
            position = index + 1
        entry.position = position
        previous = entry.value
    return result[:10]


def chamber_expenses(content: bytes, year: int) -> list[Entry]:
    totals: dict[int, Decimal] = defaultdict(Decimal)
    names = {}
    with ZipFile(BytesIO(content)) as archive:
        file = archive.getinfo(f"Ano-{year}.csv")
        if file.file_size > 160_000_000:
            raise ValueError("Arquivo de despesas excede o limite de leitura")
        with TextIOWrapper(archive.open(file), encoding="utf-8-sig") as stream:
            rows = csv.DictReader(stream, delimiter=";")
            if not {"ideCadastro", "txNomeParlamentar", "vlrLiquido", "numAno"}.issubset(
                rows.fieldnames or []
            ):
                raise ValueError("Colunas de despesas inválidas")
            for row in rows:
                if not row["ideCadastro"] or row["numAno"] != str(year):
                    continue
                identity = int(row["ideCadastro"])
                totals[identity] += Decimal(row["vlrLiquido"])
                names[identity] = row["txNomeParlamentar"]
    return [
        Entry(id=identity, name=names[identity], value=value) for identity, value in totals.items()
    ]


def senate_expenses(rows: list[dict[str, Any]], year: int) -> list[Entry]:
    totals: dict[int, Decimal] = defaultdict(Decimal)
    names = {}
    seen = set()
    for row in rows:
        if int(row["ano"]) != year or row["id"] in seen:
            continue
        seen.add(row["id"])
        identity = int(row["codSenador"])
        totals[identity] += Decimal(str(row["valorReembolsado"]))
        names[identity] = row["nomeSenador"]
    return [
        Entry(id=identity, name=names[identity], value=value) for identity, value in totals.items()
    ]


def party_snapshot(metric: MetricName, year: int) -> Ranking:
    data = Ranking(
        provider="nacional",
        metric=metric,
        year=year,
        title="Fundo Partidário" if metric == "party_fund" else "Fundo Eleitoral",
        notice="Sem curadoria de dados para este ano.",
    )
    if metric == "party_fund" and year == 2025:
        # Top five explicitly published by the TSE; allocations plus electoral fines.
        values = [
            ("PL", "192154880.51", "16490214.20"),
            ("PT", "140467359.38", "12385725.59"),
            ("UNIÃO", "107132974.30", "9770581.07"),
            ("REPUBLICANOS", "87704125.46", "7492158.80"),
            ("PSD", "84183150.69", "7167516.69"),
        ]
        data.entries = ordered(
            Entry(
                name=name,
                value=Decimal(allocation) + Decimal(fines),
                detail="Dotação orçamentária + multas eleitorais",
            )
            for name, allocation, fines in values
        )
        data.source_url, data.source_as_of = TSE_PARTY, "2026-01-15"
        data.notice = (
            "Cinco maiores repasses publicados pelo TSE no balanço de 2025. "
            "Soma da dotação e das multas repassadas. Recorte nacional, "
            "sem distribuição por poder. Revisado em 18/09/2026; atualização manual."
        )
        data.covered, data.total, data.status = 5, 19, "ready"
    elif metric == "election_fund" and year == 2026:
        election_values = [
            ("PL", "881657477.34"),
            ("PT", "615367980.20"),
            ("UNIÃO", "526242858.11"),
            ("PSD", "421008404.89"),
            ("PP", "417067738.40"),
            ("MDB", "400000239.99"),
            ("REPUBLICANOS", "348587815.77"),
            ("PODE", "245969763.68"),
            ("PDT", "169285643.92"),
            ("PSB", "152252956.07"),
            ("PSDB", "147895172.40"),
            ("PSOL", "131506284.42"),
            ("SOLIDARIEDADE", "88526669.83"),
            ("AVANTE", "72516777.19"),
            ("PRD", "71819227.37"),
            ("PC do B", "60531914.25"),
            ("CIDADANIA", "60174157.11"),
            ("PV", "45183873.26"),
            ("NOVO", "37044203.26"),
            ("REDE", "35803821.03"),
        ]
        election_values.extend(
            (name, "3307679.85")
            for name in [
                "AGIR",
                "DC",
                "DEMOCRATA",
                "MISSÃO",
                "MOBILIZA",
                "PCB",
                "PCO",
                "PRTB",
                "PSTU",
                "UP",
            ]
        )
        data.entries = ordered(
            Entry(
                name=name,
                value=Decimal(value),
                detail="Valor destinado — não comprova transferência ou gasto",
            )
            for name, value in election_values
        )
        data.source_url, data.source_as_of = TSE_ELECTION, "2026-06-03"
        data.notice = (
            "Distribuição prevista do FEFC publicada pelo TSE para 2026. "
            "Não é ranking de valores efetivamente recebidos pelas candidaturas. "
            "Recorte nacional, independente do poder; revisão manual em 18/09/2026."
        )
        data.covered, data.total, data.status = 30, 30, "ready"
    for entry in data.entries:
        entry.party = PARTIES.get(entry.name)
    return data


async def absences(client: httpx.AsyncClient, people: list[Politician], data: Ranking) -> Ranking:
    semaphore = asyncio.Semaphore(8)
    entries = []

    async def read(person: Politician) -> None:
        async with semaphore:
            try:
                response = await client.get(person.source_url, headers={"Accept": "text/html"})
                response.raise_for_status()
                dashboard = parse_dashboard(response.text, person)
                values = {m.label: m.value for m in dashboard.metrics}
                if dashboard.year != str(data.year):
                    return
                justified = int(values["Presença em Plenário - Ausências justificadas"].split()[0])
                other = int(values["Presença em Plenário - Ausências não justificadas"].split()[0])
                entries.append(
                    Entry(
                        id=person.id,
                        name=person.name,
                        photo_url=person.photo_url,
                        value=Decimal(justified + other),
                        detail=f"{justified} justificadas · {other} não justificadas",
                    )
                )
            except (httpx.HTTPError, ValueError, KeyError):
                return

    try:
        async with asyncio.timeout(180):
            await asyncio.gather(*(read(person) for person in people))
    except TimeoutError:
        pass
    data.total, data.covered = len(people), len(entries)
    data.entries = ordered(entries)
    data.status = "ready" if entries and len(entries) == len(people) else "partial"
    data.notice = (
        "Deputados atualmente em exercício. Dias de ausência em Plenário "
        "publicados no ano, incluindo justificadas. "
        "Não conta comissões nem mistura dias e reuniões. Períodos de exercício, "
        "licenças e justificativas diferem: os números não avaliam conduta. "
        "Se a cobertura for parcial, a ordem vale apenas para os perfis consultados."
    )
    data.fetched_at = datetime.now(UTC)
    data.source_url = "https://www.camara.leg.br/deputados"
    return data


async def amendment_ranking(
    client: httpx.AsyncClient, year: int, api_key: str, data: Ranking
) -> Ranking:
    if not api_key:
        data.notice = (
            "A integração está pronta, mas a chave da API do Portal da Transparência "
            "ainda não foi configurada no servidor."
        )
        return data
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    for page in range(1, 301):  # pragma: no branch - API encerra com uma página vazia
        response = await client.get(
            TRANSPARENCY_API,
            params={"ano": year, "pagina": page},
            headers={"chave-api-dados": api_key, "Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            break
        for row in rows:
            if "individual" not in str(row.get("tipoEmenda", "")).casefold():
                continue
            name = str(row.get("nomeAutor") or row.get("autor") or "").strip()
            if not name:
                continue
            value = public_money(row.get("valorEmpenhado"))
            totals[name] += value
            counts[name] += 1
    entries = [
        Entry(
            name=name,
            value=value,
            detail=f"{counts[name]} emenda(s) individual(is) com valor empenhado",
        )
        for name, value in totals.items()
    ]
    data.entries = ordered(entries)
    data.covered = len(entries)
    data.status = "ready" if entries else "unavailable"
    data.source_url = f"https://portaldatransparencia.gov.br/emendas?ano={year}"
    data.notice = (
        "Soma do valor empenhado de emendas individuais por autor no ano selecionado. "
        "Empenho é a reserva formal do recurso e não significa que o dinheiro foi pago. "
        "Emendas de bancada, comissão e relator não entram nesta comparação individual."
    )
    data.fetched_at = datetime.now(UTC)
    return data


async def ranking(
    client: httpx.AsyncClient,
    provider: Provider,
    scope: str,
    metric: MetricName,
    year: int,
    transparency_api_key: str = "",
) -> Ranking:
    if metric in {"party_fund", "election_fund"}:
        return party_snapshot(metric, year)
    data = Ranking(
        provider=scope,
        metric=metric,
        year=year,
        title={
            "expenses": "Maiores gastos com cota parlamentar",
            "absences": "Maiores ausências em Plenário",
            "approved": "Projetos aprovados",
            "amendments": "Maiores valores empenhados em emendas individuais",
        }[metric],
        unit="BRL"
        if metric in {"expenses", "amendments"}
        else "dias"
        if metric == "absences"
        else "projetos",
        notice="Fonte comparável ainda não integrada para este recorte.",
    )
    if scope not in {"camara", "senado"}:
        data.status = "not_applicable"
        data.notice = (
            "Indicador parlamentar. Para este poder, gastos individuais, produtividade "
            "e participação exigem fontes e critérios próprios ainda não integrados. "
            "Não comparamos orçamento do órgão com gasto pessoal."
        )
        return data
    if metric == "amendments":
        return await amendment_ranking(client, year, transparency_api_key, data)
    if metric == "approved":
        data.notice = (
            "Ainda sem levantamento validado de projetos e autores com aprovação "
            "final no período. Projetos apresentados e votos sobre requerimentos, "
            "emendas ou etapas intermediárias não são contados como projetos aprovados."
        )
        return data
    if metric == "absences":
        if scope == "camara":
            if year != datetime.now(UTC).year:
                data.notice = (
                    "O coletor de perfis consulta o ano corrente. "
                    "Histórico de faltas ainda não integrado; não usa dados de outro ano."
                )
                return data
            return await absences(client, await provider.search(""), data)
        data.notice = (
            "Ainda sem levantamento de ausências justificadas e não justificadas "
            "do Senado. Ausência de voto ou registro não é inferida como falta."
        )
        return data
    url = (
        f"https://www.camara.leg.br/cotas/Ano-{year}.csv.zip"
        if scope == "camara"
        else f"https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{year}"
    )
    response = await client.get(url, timeout=60)
    response.raise_for_status()
    if scope == "camara":
        try:
            entries = await run_in_threadpool(chamber_expenses, response.content, year)
        except BadZipFile as error:
            raise ValueError("Arquivo de despesas inválido") from error
    else:
        response.encoding = "utf-8"
        entries = senate_expenses(response.json(), year)
    if scope == "camara":
        for entry in entries:
            entry.photo_url = f"https://www.camara.leg.br/internet/deputado/bandep/{entry.id}.jpg"
    data.entries, data.covered = ordered(entries), len(entries)
    data.status = "ready" if entries else "unavailable"
    data.source_url = url
    data.notice = (
        "Soma dos valores líquidos da CEAP (Câmara) ou reembolsados da CEAPS (Senado) "
        "no arquivo anual oficial. Inclui parlamentares com registros no ano, "
        "mesmo fora de exercício hoje; exclui lideranças sem ID pessoal na Câmara. "
        "Não inclui salário, gabinete, emendas ou todos os custos do mandato. "
        "Não indica irregularidade e não deve ser comparado entre casas."
    )
    data.fetched_at = datetime.now(UTC)
    return data
