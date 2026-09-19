from collections import Counter
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.providers import Provider

HOUSE_SOURCE = {
    "camara": "https://dadosabertos.camara.leg.br/api/v2/deputados",
    "senado": "https://legis.senado.leg.br/dadosabertos/senador/lista/atual.json",
}


class PartySeats(BaseModel):
    party: str
    seats: int


class HouseComposition(BaseModel):
    provider: Literal["camara", "senado"]
    house: str
    total: int
    parties: list[PartySeats]
    source_url: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notice: str = (
        "Representação proporcional da composição em exercício. Os pontos não indicam "
        "a posição física de cada parlamentar no plenário."
    )


async def composition(provider: Provider, scope: Literal["camara", "senado"]) -> HouseComposition:
    people = await provider.search("")
    counts = Counter(person.party or "Sem partido informado" for person in people)
    parties = [
        PartySeats(party=party, seats=seats)
        for party, seats in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return HouseComposition(
        provider=scope,
        house="Câmara dos Deputados" if scope == "camara" else "Senado Federal",
        total=len(people),
        parties=parties,
        source_url=HOUSE_SOURCE[scope],
    )
