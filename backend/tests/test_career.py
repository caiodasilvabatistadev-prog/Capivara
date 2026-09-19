import httpx
import respx
from fastapi.testclient import TestClient

from app.career import official_career, people_by_profession, period
from app.main import app
from app.models import Politician


def person(provider: str = "camara") -> Politician:
    return Politician(
        id=1, provider=provider, name="Maria", party="X", state="SP", source_url="https://fonte"
    )


def test_period_formats_partial_and_complete_dates():
    assert period(2000, 2004) == "2000–2004"
    assert period(2000, None) == "2000"
    assert period(None, 2004) == "2004"
    assert period(None, None) == "Período não informado"


@respx.mock
async def test_official_career_and_missing_fields():
    respx.get("https://dados.test/deputados/1/profissoes").respond(
        200, json={"dados": [{"titulo": "Professora"}, {}]}
    )
    respx.get("https://dados.test/deputados/1/mandatosExternos").respond(
        200,
        json={
            "dados": [
                {
                    "cargo": "Vereadora",
                    "municipio": "Cidade",
                    "siglaUf": "SP",
                    "siglaPartidoEleicao": "X",
                    "anoInicio": 2000,
                    "anoFim": 2004,
                },
                {},
            ]
        },
    )
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        result = await official_career(client, person())
    assert result.available and result.professions[1].title == "Profissão não informada"
    assert result.previous_offices[0].detail == "Cidade · SP · X"
    assert result.previous_offices[1].title == "Cargo não informado"


@respx.mock
async def test_empty_career_and_unsupported_provider():
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        unsupported = await official_career(client, person("senado"))
        respx.get("https://dados.test/deputados/1/profissoes").respond(200, json={})
        respx.get("https://dados.test/deputados/1/mandatosExternos").respond(200, json={})
        empty = await official_career(client, person())
    assert not unsupported.available and "ainda não publica" in unsupported.notice
    assert not empty.available


@respx.mock
def test_career_route_and_invalid_id():
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").respond(
        200,
        json={
            "dados": {
                "id": 1,
                "ultimoStatus": {"nome": "Maria", "siglaPartido": "X", "siglaUf": "SP"},
            }
        },
    )
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1/profissoes").respond(
        200, json={"dados": []}
    )
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1/mandatosExternos").respond(
        200, json={"dados": []}
    )
    with TestClient(app) as client:
        assert client.get("/politicians/camara/1/career").status_code == 200
        assert client.get("/politicians/camara/0/career").status_code == 422


@respx.mock
async def test_people_by_profession_joins_current_members():
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados").respond(
        200,
        json={
            "dados": [
                {
                    "id": 1,
                    "nome": "Maria",
                    "siglaPartido": "ABC",
                    "siglaUf": "SP",
                    "urlFoto": "foto",
                    "uri": "fonte",
                    "email": "m@x",
                },
                {"id": 2, "nome": "Ana"},
            ]
        },
    )
    respx.get(
        "https://dadosabertos.camara.leg.br/arquivos/deputadosProfissoes/json/deputadosProfissoes.json"
    ).respond(
        200, json={"dados": [{"id": 1, "titulo": "Empresário"}, {"id": 2, "titulo": "Médico"}]}
    )
    async with httpx.AsyncClient(base_url="https://dadosabertos.camara.leg.br/api/v2/") as client:
        result = await people_by_profession(client, "empresário")
    assert [item.name for item in result.people] == ["Maria"]
    assert result.people[0].photo_url == "foto"


@respx.mock
def test_profession_route():
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados").respond(
        200, json={"dados": []}
    )
    respx.get(
        "https://dadosabertos.camara.leg.br/arquivos/deputadosProfissoes/json/deputadosProfissoes.json"
    ).respond(200, json=[])
    with TestClient(app) as client:
        assert client.get("/professions?name=Médico").status_code == 200
