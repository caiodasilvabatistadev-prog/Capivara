from abc import ABC, abstractmethod
from datetime import UTC, datetime
from unicodedata import normalize
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.dashboard import Dashboard, Metric, ReportBlock, ReportSection, clean, text
from app.details import (
    add_metric,
    complete_layout,
    judicial_curriculum,
    senate_profile,
    senate_resources,
)
from app.models import Politician

SENATE = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual.json"
STJ = "https://www.stj.jus.br/web/verMinistrosSTJ?parametro=1"
MINISTRIES = {
    1: ("Ministério da Saúde", "https://www.gov.br/saude/pt-br/composicao/ministro"),
    2: ("Ministério da Fazenda", "https://www.gov.br/fazenda/pt-br/composicao/ministro"),
}


def folded(value: str) -> str:
    return "".join(c for c in normalize("NFD", value.casefold()) if not 0x300 <= ord(c) <= 0x36F)


def profile(person: Politician, content: list[str]) -> Dashboard:
    return complete_layout(
        Dashboard(
            politician=person,
            year=None,
            fetched_at=datetime.now(UTC),
            updates=[],
            metrics=[
                Metric(
                    label="Cargo",
                    value=person.role,
                    group="Perfil institucional",
                    explanation="Cargo divulgado na fonte oficial.",
                ),
                Metric(
                    label="Órgão",
                    value=person.institution,
                    group="Perfil institucional",
                    explanation="Cobertura federal inicial do projeto.",
                ),
            ],
            sections=[
                ReportSection(
                    title="Perfil e contatos",
                    blocks=[ReportBlock(kind="text", text=line) for line in content],
                )
            ],
        )
    )


class DirectoryProvider(ABC):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    @abstractmethod
    async def listing(self) -> list[Dashboard]: ...

    async def search(self, name: str) -> list[Politician]:
        return [
            data.politician
            for data in await self.listing()
            if folded(name) in folded(data.politician.name)
        ]

    async def get(self, official_id: int) -> Politician:
        return (await self.dashboard(official_id)).politician

    async def dashboard(self, official_id: int) -> Dashboard:
        for data in await self.listing():
            if data.politician.id == official_id:
                return data
        raise HTTPException(404, "Autoridade não encontrada")


class SenateProvider(DirectoryProvider):
    async def get(self, official_id: int) -> Politician:
        return (await DirectoryProvider.dashboard(self, official_id)).politician

    async def dashboard(self, official_id: int) -> Dashboard:
        data = await super().dashboard(official_id)
        year = datetime.now(UTC).year
        sources = [
            (data.politician.source_url, senate_profile),
            (
                f"https://www6g.senado.leg.br/transparencia/sen/{official_id}/?ano={year}",
                senate_resources,
            ),
        ]
        source_blocks = []
        for url, parser in sources:
            try:
                response = await self.client.get(url, headers={"Accept": "text/html"})
                response.raise_for_status()
                parser(data, response.text)
                state = "Consultada"
            except (httpx.HTTPError, ValueError):
                state = "Indisponível ou estrutura inválida nesta consulta"
            source_blocks.append(ReportBlock(kind="text", text=state + ": " + url))
        data.sections.append(ReportSection(title="Fontes e cobertura", blocks=source_blocks))
        return data

    async def listing(self) -> list[Dashboard]:
        response = await self.client.get(SENATE)
        response.raise_for_status()
        response.encoding = "utf-8"
        items = response.json()["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
        result = []
        for item in items:
            info = item["IdentificacaoParlamentar"]
            person = Politician(
                id=int(info["CodigoParlamentar"]),
                provider="senado",
                role="Senador(a)",
                institution="Senado Federal",
                name=info["NomeParlamentar"],
                party=info["SiglaPartidoParlamentar"],
                state=info["UfParlamentar"],
                email=info.get("EmailParlamentar"),
                photo_url=info.get("UrlFotoParlamentar", "").replace("http://", "https://") or None,
                source_url=info["UrlPaginaParlamentar"].replace("http://", "https://"),
            )
            mandate = item.get("Mandato", {})
            result.append(
                profile(
                    person,
                    [
                        f"Nome completo: {info.get('NomeCompletoParlamentar', person.name)}",
                        f"Partido: {person.party} | UF: {person.state}",
                        f"E-mail: {person.email or 'Não informado'}",
                        "Participação no mandato: "
                        + mandate.get("DescricaoParticipacao", "Não informado"),
                    ],
                )
            )
        return result


class ExecutiveProvider(DirectoryProvider):
    async def listing(self) -> list[Dashboard]:
        result = []
        for identity, (institution, url) in MINISTRIES.items():
            response = await self.client.get(url, headers={"Accept": "text/html"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            if identity == 2:
                link = soup.select_one('#content-core a[href*="/composicao/ministro/"]')
                if link is None:
                    raise ValueError("Lista de autoridades inválida")
                url = urljoin(url, str(link["href"]))
                response = await self.client.get(url, headers={"Accept": "text/html"})
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
            heading, role = (
                soup.select_one("h1.documentFirstHeading"),
                soup.select_one(".autoridade"),
            )
            if heading is None or role is None:
                raise ValueError("Perfil de autoridade inválido")
            image, email = soup.select_one(".item img"), soup.select_one(".email")
            person = Politician(
                id=identity,
                provider="executivo",
                power="executivo",
                role=text(role),
                institution=institution,
                name=text(heading),
                party="Não informado",
                state="Brasil",
                email=clean(text(email).split(":", 1)[-1]) if email else None,
                photo_url=urljoin(url, str(image["src"])) if image else None,
                source_url=url,
            )
            result.append(
                profile(
                    person,
                    [
                        text(role),
                        text(soup.select_one(".telefone")),
                        text(email),
                        text(soup.select_one(".descricao_pessoa")),
                    ],
                )
            )
        return result

    async def dashboard(self, official_id: int) -> Dashboard:
        data = await super().dashboard(official_id)
        contact = data.sections[0].blocks
        add_metric(
            data,
            "Telefone institucional",
            contact[1].text,
            "Perfil institucional",
            "Contato publicado na página oficial da autoridade.",
        )
        add_metric(
            data,
            "E-mail institucional",
            contact[2].text,
            "Perfil institucional",
            "Contato publicado na página oficial da autoridade.",
        )
        data.sections.append(ReportSection(title="Currículo e trajetória", blocks=[contact[3]]))
        data.sections[0].blocks = contact[:3]
        data.sections.append(
            ReportSection(
                title="Fontes e cobertura",
                blocks=[
                    ReportBlock(kind="text", text=data.politician.source_url),
                    ReportBlock(
                        kind="text",
                        text="Currículo e contatos consultados. "
                        "Agenda do e-Agendas e remuneração do "
                        "Portal da Transparência exigem integrações autenticadas "
                        "ainda não configuradas. "
                        "Orçamento do ministério não é gasto pessoal do ministro. "
                        "Propostas legislativas "
                        "e emendas de autoria parlamentar não são indicadores deste cargo.",
                    ),
                ],
            )
        )
        return data


class JudicialProvider(DirectoryProvider):
    async def listing(self) -> list[Dashboard]:
        response = await self.client.get(STJ, headers={"Accept": "text/html"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select(".clsMinistrosLinha")
        if not rows:
            raise ValueError("Lista de ministros inválida")
        result = []
        for row in rows:
            link = row.select_one(".clsMinistrosNome a")
            if link is None:
                raise ValueError("Ministro sem identificação")
            url = urljoin(STJ, str(link["href"]))
            identity = int(parse_qs(urlparse(url).query)["cod_matriculamin"][0])
            person = Politician(
                id=identity,
                provider="judiciario",
                power="judiciario",
                role="Ministro(a) do STJ",
                institution="Superior Tribunal de Justiça",
                name=text(link),
                party="Não se aplica",
                state="Brasil",
                source_url=url,
            )
            result.append(
                profile(
                    person,
                    [
                        f"Naturalidade (UF): {text(row.select_one('.clsMinistrosNaturalidade'))}",
                        "Integrante da lista oficial de ministros em atividade.",
                    ],
                )
            )
        return result

    async def dashboard(self, official_id: int) -> Dashboard:
        data = await super().dashboard(official_id)
        response = await self.client.get(
            data.politician.source_url, headers={"Accept": "text/html"}
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        curriculum = soup.select_one(f".curriculo{official_id:07d}")
        if curriculum is None:
            raise ValueError("Currículo inválido")
        image = curriculum.select_one("img")
        data.politician.photo_url = (
            urljoin(data.politician.source_url, str(image["src"])) if image else None
        )
        data.sections.append(
            ReportSection(
                title="Fontes e cobertura",
                blocks=[
                    ReportBlock(kind="text", text=data.politician.source_url),
                    ReportBlock(
                        kind="text",
                        text="Currículo oficial consultado. Remuneração, "
                        "produtividade individual, decisões e "
                        "agenda não estão integradas. "
                        "Orçamento do STJ não é gasto pessoal do ministro. "
                        "Emendas de autoria parlamentar não se aplicam ao cargo.",
                    ),
                ],
            )
        )
        judicial_curriculum(data, curriculum)
        return data
