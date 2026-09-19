from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel

from app.dashboard import Dashboard, ReportBlock, ReportSection
from app.models import Politician

SOURCE = "https://www.tse.jus.br/partidos/partidos-registrados-no-tse"
REVIEWED = "2026-09-18"


class Party(BaseModel):
    id: int
    sigla: str
    president: str
    background: str = "#203342"
    logo_url: str
    source_url: str = SOURCE
    reviewed_at: str = REVIEWED


PARTIES = {
    "PL": Party(
        id=22,
        sigla="PL",
        background="#163f66",
        president="Valdemar Costa Neto",
        logo_url="/parties/22.png",
    ),
    "PT": Party(
        id=13,
        sigla="PT",
        background="#642835",
        president="Edinho Silva",
        logo_url="/parties/13.svg",
    ),
    "UNIÃO": Party(
        id=44,
        sigla="UNIÃO",
        background="#234f64",
        president="Antonio Rueda",
        logo_url="/parties/44.png",
    ),
    "PSD": Party(
        id=55,
        sigla="PSD",
        background="#3a5136",
        president="Gilberto Kassab",
        logo_url="/parties/55.png",
    ),
    "REPUBLICANOS": Party(
        id=10,
        sigla="REPUBLICANOS",
        background="#23496b",
        president="Marcos Pereira",
        logo_url="/parties/10.png",
    ),
    "PP": Party(
        id=11,
        sigla="PP",
        background="#254966",
        president="Ciro Nogueira",
        logo_url="/parties/11.png",
    ),
    "MDB": Party(
        id=15,
        sigla="MDB",
        background="#2a573d",
        president="Baleia Rossi",
        logo_url="/parties/15.svg",
    ),
    "PODE": Party(
        id=20,
        sigla="PODE",
        background="#493462",
        president="Renata Abreu",
        logo_url="/parties/20.png",
    ),
    "PDT": Party(
        id=12,
        sigla="PDT",
        background="#304556",
        president="Carlos Lupi",
        logo_url="/parties/12.png",
    ),
    "PSB": Party(
        id=40,
        sigla="PSB",
        background="#69313e",
        president="João Campos",
        logo_url="/parties/40.png",
    ),
}


class PartyProvider:
    async def search(self, name: str) -> list[Politician]:
        return [
            await self.get(p.id)
            for p in PARTIES.values()
            if name.casefold() in p.president.casefold()
        ]

    async def get(self, official_id: int) -> Politician:
        party = next((p for p in PARTIES.values() if p.id == official_id), None)
        if party is None:
            raise HTTPException(404, "Presidente partidário não cadastrado")
        return Politician(
            id=party.id,
            provider="partidos",
            power="partidario",
            name=party.president,
            party=party.sigla,
            role="Presidente nacional de partido",
            institution="Tribunal Superior Eleitoral",
            state="Nacional",
            source_url=party.source_url,
        )

    async def dashboard(self, official_id: int) -> Dashboard:
        person = await self.get(official_id)
        return Dashboard(
            politician=person,
            year=None,
            fetched_at=datetime.now(UTC),
            updates=[],
            metrics=[],
            notice=(
                "Perfil da presidência nacional, conferido no cadastro do TSE em 18/09/2026. "
                "Atualização manual. O cargo partidário não comprova candidatura ou mandato. "
                "Recursos dos fundos pertencem ao partido, não ao presidente pessoalmente."
            ),
            sections=[
                ReportSection(
                    title="Presidência nacional e fonte",
                    blocks=[
                        ReportBlock(
                            kind="text", text=f"{person.party}: {person.name}. Fonte: {SOURCE}"
                        ),
                        ReportBlock(
                            kind="text",
                            text="Este perfil apresenta o cargo partidário. "
                            "Dados de eventual mandato são consultados pela busca "
                            "da casa correspondente; "
                            "gastos, emendas e votos não são atribuídos "
                            "ao cargo de presidente partidário.",
                        ),
                    ],
                )
            ],
        )
