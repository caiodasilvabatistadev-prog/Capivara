import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app

BASE = "https://dadosabertos.camara.leg.br/api/v2/"
ITEM = {"id": 1, "nome": "Maria", "siglaPartido": "ABC", "siglaUf": "SP"}


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    [
        "/search?q=a",
        "/search?q=%20%20",
        "/search",
        "/politicians/camara/0",
        "/politicians/camara/no",
        "/politicians/other/1",
    ],
)
def test_validation(client, path):
    assert client.get(path).status_code in (404, 422)


@respx.mock
def test_search_pagination(client):
    route = respx.get(BASE + "deputados").mock(
        side_effect=[
            httpx.Response(200, json={"dados": [ITEM], "links": [{"rel": "next"}]}),
            httpx.Response(200, json={"dados": [], "links": []}),
        ]
    )
    response = client.get("/search?q=%20Maria%20")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Maria"
    assert route.calls[0].request.url.params["nome"] == "Maria"
    assert route.calls[1].request.url.params["pagina"] == "2"


@respx.mock
def test_empty(client):
    respx.get(BASE + "deputados").respond(200, json={"dados": []})
    assert client.get("/search?q=Maria").json() == []


@respx.mock
def test_detail(client):
    respx.get(BASE + "deputados/1").respond(
        200,
        json={
            "dados": {
                "id": 1,
                "ultimoStatus": {
                    **ITEM,
                    "email": "maria@example.org",
                    "urlFoto": "https://example.org/photo",
                },
            }
        },
    )
    data = client.get("/politicians/camara/1").json()
    assert data["email"] == "maria@example.org"
    assert data["source_url"] == "https://www.camara.leg.br/deputados/1"


@pytest.mark.parametrize("status", [404, 429, 500])
@respx.mock
def test_upstream_status(client, status):
    respx.get(BASE + "deputados/1").respond(status)
    assert client.get("/politicians/camara/1").status_code == (404 if status == 404 else 502)


@respx.mock
def test_timeout(client):
    respx.get(BASE + "deputados").mock(side_effect=httpx.ReadTimeout("timeout"))
    assert client.get("/search?q=Maria").status_code == 502


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"dados": [{"id": 1}]},
        {"dados": [{**ITEM, "id": "bad"}]},
        {"dados": [{**ITEM, "nome": None}]},
        {"dados": None},
    ],
)
@respx.mock
def test_malformed(client, payload):
    respx.get(BASE + "deputados").respond(200, json=payload)
    assert client.get("/search?q=Maria").status_code == 502


@respx.mock
def test_invalid_json(client):
    respx.get(BASE + "deputados").respond(200, text="invalid")
    assert client.get("/search?q=Maria").status_code == 502
