import respx
from fastapi.testclient import TestClient

from app.composition import composition
from app.main import app
from app.models import Politician


class FakeProvider:
    async def search(self, name: str) -> list[Politician]:
        assert name == ""
        return [
            Politician(id=1, name="Ana", party="B", state="SP", source_url="https://a"),
            Politician(id=2, name="Bia", party="A", state="RJ", source_url="https://b"),
            Politician(id=3, name="Caio", party="A", state="MG", source_url="https://c"),
        ]


async def test_composition_counts_and_orders_parties():
    data = await composition(FakeProvider(), "senado")  # type: ignore[arg-type]
    assert data.house == "Senado Federal" and data.total == 3
    assert [(item.party, item.seats) for item in data.parties] == [("A", 2), ("B", 1)]
    assert data.source_url.endswith("atual.json")


@respx.mock
def test_composition_route_and_validation():
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados").respond(
        200,
        json={
            "dados": [
                {"id": 1, "nome": "Ana", "siglaPartido": "ABC", "siglaUf": "SP"},
                {"id": 2, "nome": "Bia", "siglaPartido": "", "siglaUf": "RJ"},
            ],
            "links": [],
        },
    )
    with TestClient(app) as client:
        data = client.get("/composition/camara").json()
        assert data["house"] == "Câmara dos Deputados"
        assert data["total"] == 2
        assert data["parties"][1]["party"] == "Sem partido informado"
        assert client.get("/composition/executivo").status_code == 422
