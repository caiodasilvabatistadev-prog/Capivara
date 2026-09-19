import csv
from datetime import UTC, datetime
from io import BytesIO, TextIOWrapper
from zipfile import BadZipFile, ZipFile

import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.dashboard import Dashboard, Metric, ReportBlock, ReportSection
from app.directories import folded
from app.models import Politician


class DemographicGroup(BaseModel):
    label: str
    value: int
    percentage: float


class DemographicSnapshot(BaseModel):
    year: int
    scope: str
    total: int
    sex_total: int
    race_total: int
    sex: list[DemographicGroup]
    race: list[DemographicGroup]
    source_url: str
    notice: str


def published_2024_snapshot() -> DemographicSnapshot:
    sex_total = 456_310
    race = {
        "Branca": 217_020,
        "Parda": 186_746,
        "Preta": 52_451,
        "Não informado": 2_763,
        "Indígena": 2_578,
        "Amarela": 1_790,
        "Não divulgável": 46,
    }
    race_total = sum(race.values())

    def group(label: str, value: int, total: int) -> DemographicGroup:
        return DemographicGroup(label=label, value=value, percentage=round(value * 100 / total, 2))

    return DemographicSnapshot(
        year=2024,
        scope="Candidaturas registradas em publicação consolidada do TSE",
        total=race_total,
        sex_total=sex_total,
        race_total=race_total,
        sex=[group("Homens", 301_310, sex_total), group("Mulheres", 155_000, sex_total)],
        race=[group(label, value, race_total) for label, value in race.items()],
        source_url=(
            "https://www.tse.jus.br/institucional/catalogo-de-publicacoes/arquivos/"
            "analise-da-distribuicao-de-candidaturas-vagas-de-eleitos-e-recursos-de-"
            "financiamento-por-perfil-racial/@@display-file/file/"
            "Relatorio_estatistico_digital.pdf"
        ),
        notice=(
            "Contingência baseada em totais consolidados publicados pelo TSE. "
            "Os universos de sexo e raça/cor usam publicações oficiais distintas e, por isso, "
            "possuem totais próprios. Não representam mandatos atualmente em exercício."
        ),
    )


class ElectionProvider:
    def __init__(self, client: httpx.AsyncClient, year: int) -> None:
        self.client = client
        self.year = year
        self.url = (
            f"https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{year}.zip"
        )
        self.page = f"https://dadosabertos.tse.jus.br/dataset/candidatos-{year}"

    def read(self, content: bytes, query: str | int) -> list[dict[str, str]]:
        try:
            with ZipFile(BytesIO(content)) as archive:
                files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                brazil = [name for name in files if name.upper().endswith("_BRASIL.CSV")]
                result = {}
                for name in brazil or files:
                    with (
                        archive.open(name) as stream,
                        TextIOWrapper(stream, encoding="cp1252") as text,
                    ):
                        for row in csv.DictReader(text, delimiter=";"):
                            identity = int(row["SQ_CANDIDATO"])
                            names = folded(row["NM_CANDIDATO"] + " " + row["NM_URNA_CANDIDATO"])
                            matches = (
                                identity == query
                                if isinstance(query, int)
                                else all(token in names for token in folded(query).split())
                            )
                            if matches:
                                result[identity] = row
                return list(result.values())
        except BadZipFile as error:
            raise ValueError("Arquivo eleitoral inválido") from error

    async def records(self, query: str | int) -> list[dict[str, str]]:
        response = await self.client.get(self.url, timeout=60)
        response.raise_for_status()
        return await run_in_threadpool(self.read, response.content, query)

    def read_demographics(self, content: bytes) -> DemographicSnapshot:
        try:
            candidates: dict[int, tuple[str, str]] = {}
            with ZipFile(BytesIO(content)) as archive:
                files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                brazil = [name for name in files if name.upper().endswith("_BRASIL.CSV")]
                for name in brazil or files:
                    with (
                        archive.open(name) as stream,
                        TextIOWrapper(stream, encoding="cp1252") as text,
                    ):
                        for row in csv.DictReader(text, delimiter=";"):
                            if row.get("DS_SITUACAO_CANDIDATURA") != "APTO":
                                continue
                            candidates[int(row["SQ_CANDIDATO"])] = (
                                row.get("DS_GENERO", "NÃO INFORMADO"),
                                row.get("DS_COR_RACA", "NÃO INFORMADO"),
                            )
        except BadZipFile as error:
            raise ValueError("Arquivo eleitoral inválido") from error
        total = len(candidates)

        def groups(index: int) -> list[DemographicGroup]:
            counts: dict[str, int] = {}
            for values in candidates.values():
                label = values[index] or "NÃO INFORMADO"
                counts[label] = counts.get(label, 0) + 1
            return [
                DemographicGroup(
                    label=label.title(),
                    value=value,
                    percentage=round(value * 100 / total, 2) if total else 0,
                )
                for label, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]

        return DemographicSnapshot(
            year=self.year,
            scope="Candidaturas aptas",
            total=total,
            sex_total=total,
            race_total=total,
            sex=groups(0),
            race=groups(1),
            source_url=self.page,
            notice=(
                "Sexo e raça/cor são autodeclarados no registro de candidatura. "
                "Este recorte não representa os mandatos atualmente em exercício."
            ),
        )

    async def demographics(self) -> DemographicSnapshot:
        response = await self.client.get(self.url, timeout=60)
        if response.status_code == 403 and self.year == 2024:
            return published_2024_snapshot()
        response.raise_for_status()
        return await run_in_threadpool(self.read_demographics, response.content)

    def person(self, row: dict[str, str]) -> Politician:
        cargo = row["DS_CARGO"]
        return Politician(
            id=int(row["SQ_CANDIDATO"]),
            provider=f"tse{self.year}",
            name=row["NM_URNA_CANDIDATO"],
            role=f"Candidatura {self.year} · {cargo}",
            institution=f"Justiça Eleitoral · {row['NM_UE']}",
            power="legislativo"
            if cargo
            in {
                "VEREADOR",
                "DEPUTADO FEDERAL",
                "DEPUTADO ESTADUAL",
                "DEPUTADO DISTRITAL",
                "SENADOR",
                "1º SUPLENTE",
                "2º SUPLENTE",
            }
            else "executivo",
            party=row["SG_PARTIDO"],
            state=row["SG_UF"],
            source_url=self.page,
        )

    async def search(self, name: str) -> list[Politician]:
        return [self.person(row) for row in await self.records(name)]

    async def get(self, official_id: int) -> Politician:
        return (await self.dashboard(official_id)).politician

    async def dashboard(self, official_id: int) -> Dashboard:
        rows = await self.records(official_id)
        if not rows:
            raise HTTPException(404, "Candidatura não encontrada")
        row = rows[0]
        person = self.person(row)
        # CPF, título eleitoral e e-mail particular não são exibidos nem exportados.
        fields = [
            "NM_CANDIDATO",
            "NM_URNA_CANDIDATO",
            "NR_CANDIDATO",
            "DS_CARGO",
            "SG_PARTIDO",
            "NM_PARTIDO",
            "NM_FEDERACAO",
            "NM_COLIGACAO",
            "SG_UF",
            "NM_UE",
            "DS_SITUACAO_CANDIDATURA",
            "DS_DETALHE_SITUACAO_CAND",
            "DS_SIT_TOT_TURNO",
            "DS_OCUPACAO",
            "DS_GRAU_INSTRUCAO",
            "DS_NACIONALIDADE",
            "ANO_ELEICAO",
            "NR_TURNO",
            "DT_GERACAO",
            "HH_GERACAO",
        ]
        return Dashboard(
            politician=person,
            year=str(self.year),
            fetched_at=datetime.now(UTC),
            updates=[],
            metrics=[
                Metric(
                    label="Registro eleitoral",
                    value=row.get("DS_SITUACAO_CANDIDATURA", "Não informado"),
                    group="Candidatura",
                    explanation=(
                        "Situação do registro publicada no arquivo do TSE; não "
                        "indica condenação criminal."
                    ),
                )
            ],
            sections=[
                ReportSection(
                    title="Dados eleitorais",
                    blocks=[
                        ReportBlock(
                            kind="table",
                            text="Cadastro de candidatura do TSE",
                            rows=[["Campo", "Valor"]]
                            + [
                                [key.replace("_", " ").capitalize(), row[key]]
                                for key in fields
                                if key in row
                            ],
                        )
                    ],
                ),
                ReportSection(
                    title="Fontes e cobertura",
                    blocks=[
                        ReportBlock(kind="text", text=self.page),
                        ReportBlock(kind="text", text=self.url),
                    ],
                ),
            ],
            notice=(
                f"Candidatura registrada na base eleitoral de {self.year}. "
                f"Não comprova cargo ou filiação partidária atuais. Situação "
                f"eleitoral não equivale a situação criminal. Patrimônio e "
                f"contas de campanha pertencem a bases separadas, ainda não "
                f"integradas. Dados particulares de identificação não são "
                f"exibidos."
            ),
        )
