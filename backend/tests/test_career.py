import httpx
import respx
from fastapi.testclient import TestClient

from app.career import claim_ids, official_career, people_by_profession, period
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
    wikipedia = respx.get("https://pt.wikipedia.org/w/rest.php/v1/search/page").mock(
        return_value=httpx.Response(200, json={"pages": []})
    )
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        unsupported = await official_career(client, person("senado"))
        respx.get("https://dados.test/deputados/1/profissoes").respond(200, json={})
        respx.get("https://dados.test/deputados/1/mandatosExternos").respond(200, json={})
        empty = await official_career(client, person())
    assert not unsupported.available and "ainda não publica" in unsupported.notice
    assert not empty.available
    assert wikipedia.call_count == 2


def test_claim_ids_ignores_invalid_and_duplicate_claims():
    assert claim_ids(
        {
            "claims": {
                "P106": [
                    {"mainsnak": {"datavalue": {"value": {"id": "Q1"}}}},
                    {"mainsnak": {"datavalue": {"value": {"id": "Q1"}}}},
                    {"mainsnak": {}},
                ]
            }
        },
        "P106",
    ) == ["Q1"]
    assert claim_ids({}, "P106") == []


@respx.mock
async def test_wikimedia_fallback_for_non_camara_profile():
    respx.get("https://pt.wikipedia.org/w/rest.php/v1/search/page").respond(
        200,
        json={"pages": [{"title": "Homônimo"}, {"title": "Maria"}]},
    )
    respx.get("https://pt.wikipedia.org/api/rest_v1/page/summary/Maria").respond(
        200,
        json={
            "wikibase_item": "Q1",
            "content_urls": {"desktop": {"page": "https://pt.wikipedia.org/wiki/Maria"}},
        },
    )
    respx.get("https://www.wikidata.org/wiki/Special:EntityData/Q1.json").respond(
        200,
        json={
            "entities": {
                "Q1": {
                    "claims": {
                        "P106": [
                            {"mainsnak": {"datavalue": {"value": {"id": "Q2"}}}},
                            {"mainsnak": {"datavalue": {"value": {"id": "Q4"}}}},
                        ],
                        "P39": [{"mainsnak": {"datavalue": {"value": {"id": "Q3"}}}}],
                    }
                }
            }
        },
    )
    respx.get("https://www.wikidata.org/w/api.php").respond(
        200,
        json={
            "entities": {
                "Q2": {"labels": {"pt": {"value": "Metalúrgica"}}},
                "Q3": {"labels": {"pt": {"value": "Presidente do Brasil"}}},
                "Q4": {"labels": {"en": {"value": "English only"}}},
            }
        },
    )
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        result = await official_career(client, person("presidentes"))
    assert result.available
    assert result.source_kind == "complementary"
    assert result.source_name == "Wikidata e Wikipédia"
    assert len(result.professions) == 1
    assert result.professions[0].title == "Metalúrgica"
    assert result.previous_offices[0].title == "Presidente do Brasil"


@respx.mock
async def test_wikimedia_fallback_handles_missing_or_failed_data():
    search = respx.get("https://pt.wikipedia.org/w/rest.php/v1/search/page")
    search.respond(200, json={"pages": [{"title": "Outra Maria"}]})
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        missing = await official_career(client, person("presidentes"))
    assert not missing.available
    search.respond(503)
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        failed = await official_career(client, person("presidentes"))
    assert not failed.available


@respx.mock
async def test_wikimedia_fallback_handles_summary_without_entity_and_empty_claims():
    respx.get("https://pt.wikipedia.org/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "Maria"}]}
    )
    summary = respx.get("https://pt.wikipedia.org/api/rest_v1/page/summary/Maria")
    summary.respond(200, json={})
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        without_entity = await official_career(client, person("presidentes"))
    assert not without_entity.available

    summary.respond(200, json={"wikibase_item": "Q1"})
    respx.get("https://www.wikidata.org/wiki/Special:EntityData/Q1.json").respond(
        200, json={"entities": {"Q1": {"claims": {}}}}
    )
    async with httpx.AsyncClient(base_url="https://dados.test/") as client:
        empty = await official_career(client, person("presidentes"))
    assert not empty.available
    assert empty.source_url.endswith("/wiki/Maria")


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
    respx.get("https://pt.wikipedia.org/w/rest.php/v1/search/page").respond(200, json={"pages": []})
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
