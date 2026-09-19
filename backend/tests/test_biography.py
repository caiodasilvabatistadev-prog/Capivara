import httpx
import respx
from fastapi.testclient import TestClient

from app.biography import WIKIPEDIA, folded, wikipedia_biography
from app.main import app
from app.models import Politician

PERSON = Politician(
    id=1,
    name="José Árvore",
    party="ABC",
    state="SP",
    source_url="https://www.camara.leg.br/deputados/1",
)


@respx.mock
async def test_wikipedia_exact_name_and_safe_fallbacks():
    respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "Outro"}, {"title": "José Árvore"}]}
    )
    respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Jos%C3%A9%20%C3%81rvore").respond(
        200,
        json={
            "title": "José Árvore",
            "description": "político brasileiro",
            "extract": "José é um político brasileiro.",
            "content_urls": {"desktop": {"page": "https://pt.wikipedia.org/wiki/José_Árvore"}},
        },
    )
    async with httpx.AsyncClient() as client:
        data = await wikipedia_biography(client, PERSON)
    assert data.found and data.extract.startswith("José")
    assert data.source_url.endswith("José_Árvore")
    assert folded("  JOSÉ Árvore  ") == "jose arvore"


@respx.mock
async def test_wikipedia_rejects_homonym_and_empty_article():
    search = respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "José Árvore (cantor)"}]}
    )
    async with httpx.AsyncClient() as client:
        assert not (await wikipedia_biography(client, PERSON)).found
        search.respond(200, json={"pages": [{"title": "José Árvore"}]})
        respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Jos%C3%A9%20%C3%81rvore").respond(
            200, json={"extract": "", "content_urls": None}
        )
        assert not (await wikipedia_biography(client, PERSON)).found


@respx.mock
def test_biography_route_and_invalid_identity():
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").respond(
        200,
        json={
            "dados": {
                "id": 1,
                "ultimoStatus": {"nome": "Maria", "siglaPartido": "X", "siglaUf": "SP"},
            }
        },
    )
    respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(200, json={"pages": []})
    with TestClient(app) as client:
        assert client.get("/politicians/camara/1/biography").json()["found"] is False
        assert client.get("/politicians/camara/0/biography").status_code == 422
