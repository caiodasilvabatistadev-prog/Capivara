import asyncio
from dataclasses import dataclass

import httpx

from app.dashboard import Dashboard
from app.directories import DirectoryProvider, folded, profile
from app.models import Politician
from app.providers import CamaraProvider


@dataclass(frozen=True)
class Figure:
    id: int
    name: str
    role: str
    institution: str
    source_url: str
    state: str = "Brasil"
    note: str = "Registro biográfico e institucional."


STF_FIGURES = [
    Figure(
        1,
        "Gilmar Mendes",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        2,
        "Cármen Lúcia",
        "Ministra do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        3,
        "Dias Toffoli",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        4,
        "Luiz Fux",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        5,
        "Edson Fachin",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        6,
        "Alexandre de Moraes",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        7,
        "Nunes Marques",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        8,
        "André Mendonça",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        9,
        "Cristiano Zanin",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        10,
        "Flávio Dino",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
    Figure(
        11,
        "Jorge Messias",
        "Ministro do STF",
        "Supremo Tribunal Federal",
        "https://portal.stf.jus.br/ministros/",
    ),
]

PRESIDENTS = [
    Figure(
        101,
        "José Sarney",
        "Ex-presidente da República",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
    ),
    Figure(
        102,
        "Fernando Collor de Mello",
        "Ex-presidente da República",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
    ),
    Figure(
        103,
        "Itamar Franco",
        "Ex-presidente da República · falecido",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
        note="Perfil histórico. Falecido em 2011.",
    ),
    Figure(
        104,
        "Fernando Henrique Cardoso",
        "Ex-presidente da República",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
    ),
    Figure(
        105,
        "Dilma Rousseff",
        "Ex-presidente da República",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
    ),
    Figure(
        106,
        "Michel Temer",
        "Ex-presidente da República",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
    ),
    Figure(
        107,
        "Jair Bolsonaro",
        "Ex-presidente da República",
        "Presidência da República",
        "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/galeria-de-presidentes",
    ),
]


class CatalogProvider(DirectoryProvider):
    def __init__(self, client: httpx.AsyncClient, provider: str, figures: list[Figure]) -> None:
        super().__init__(client)
        self.provider = provider
        self.figures = figures

    async def listing(self) -> list[Dashboard]:
        return [
            profile(
                Politician(
                    id=item.id,
                    provider=self.provider,
                    role=item.role,
                    institution=item.institution,
                    power="judiciario" if self.provider == "stf" else "executivo",
                    name=item.name,
                    party="Não se aplica",
                    state=item.state,
                    source_url=item.source_url,
                ),
                [item.note, f"Fonte oficial: {item.source_url}"],
            )
            for item in self.figures
        ]


class HistoricalCamaraProvider(CamaraProvider):
    async def search(self, name: str) -> list[Politician]:
        async def legislature(number: int) -> list[Politician]:
            response = await self.client.get(
                "deputados", params={"nome": name, "idLegislatura": number, "itens": 100}
            )
            response.raise_for_status()
            return [self.normalize(item) for item in response.json()["dados"]]

        batches = await asyncio.gather(*(legislature(number) for number in range(48, 57)))
        unique = {person.id: person for batch in batches for person in batch}
        result = []
        for person in unique.values():
            person.provider = "camara_historica"
            person.role = "Ex-deputado(a) federal · acervo histórico"
            result.append(person)
        return sorted(result, key=lambda person: folded(person.name))

    async def get(self, official_id: int) -> Politician:
        person = await super().get(official_id)
        person.provider = "camara_historica"
        person.role = "Ex-deputado(a) federal · acervo histórico"
        return person

    async def dashboard(self, official_id: int) -> Dashboard:
        person = await self.get(official_id)
        return profile(
            person,
            [
                "Registro do acervo histórico da Câmara dos Deputados.",
                f"Fonte oficial: {person.source_url}",
            ],
        )
