import httpx
import respx
from fastapi.testclient import TestClient

from app.biography import WIKIPEDIA
from app.family import WIKIDATA, documented_family, has_political_profile
from app.main import app
from app.models import Politician

PERSON = Politician(
    id=1, name="Maria Silva", party="X", state="SP", source_url="https://example.com"
)


@respx.mock
async def test_family_requires_exact_article_and_wikidata_id():
    search = respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "Homônima"}]}
    )
    async with httpx.AsyncClient() as client:
        assert not (await documented_family(client, PERSON)).found
        search.respond(200, json={"pages": [{"title": "Maria Silva"}]})
        respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Maria%20Silva").respond(200, json={})
        assert not (await documented_family(client, PERSON)).found


async def test_family_uses_curated_tree_before_external_lookup():
    cassio = PERSON.model_copy(update={"name": "Cássio Cunha Lima"})
    async with httpx.AsyncClient() as client:
        result = await documented_family(client, cassio)
    assert result.found
    assert {member.name for member in result.members} == {
        "Ronaldo Cunha Lima",
        "Pedro Cunha Lima",
        "Romero Rodrigues",
        "Fernando Rodrigues Catão",
    }
    assert result.source_url.startswith("https://dspace.sti.ufcg.edu.br/")
    assert sum(member.political_profile for member in result.members) == 3
    assert not next(
        member for member in result.members if member.name == "Fernando Rodrigues Catão"
    ).political_profile


def test_political_profile_detection():
    assert has_political_profile("Deputada federal de São Paulo")
    assert has_political_profile("Ministra do STF")
    assert not has_political_profile("Advogada brasileira")


@respx.mock
async def test_family_keeps_only_referenced_relationships_and_resolves_labels():
    respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "Maria Silva"}]}
    )
    respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Maria%20Silva").respond(
        200, json={"wikibase_item": "Q1"}
    )
    entity = respx.get(WIKIDATA + "/wiki/Special:EntityData/Q1.json")
    entity.respond(
        200,
        json={
            "entities": {
                "Q1": {
                    "claims": {
                        "P22": [
                            {"mainsnak": {"datavalue": {"value": {"id": "Q2"}}}, "references": [{}]}
                        ],
                        "P25": [{"mainsnak": {"datavalue": {"value": {"id": "Q3"}}}}],
                        "P26": [
                            {"mainsnak": {"datavalue": {"value": "inválido"}}, "references": [{}]}
                        ],
                        "P40": [
                            {"mainsnak": {"datavalue": {"value": {"id": "Q4"}}}, "references": [{}]}
                        ],
                        "P3373": [],
                    }
                }
            }
        },
    )
    respx.get(WIKIDATA + "/w/api.php").respond(
        200,
        json={
            "entities": {
                "Q2": {
                    "labels": {"pt": {"value": "João"}},
                    "descriptions": {"pt": {"value": "político"}},
                },
                "Q4": {"labels": {"en": {"value": "Ana"}}, "descriptions": {}},
            }
        },
    )
    async with httpx.AsyncClient() as client:
        result = await documented_family(client, PERSON)
    assert result.found
    assert [(item.name, item.relationship) for item in result.members] == [
        ("João", "pai"),
        ("Ana", "filho(a)"),
    ]
    assert result.members[0].description == "político"
    assert result.members[0].political_profile
    assert result.members[1].description == ""
    assert not result.members[1].political_profile


@respx.mock
async def test_family_returns_empty_when_claims_have_no_proof():
    respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "Maria Silva"}]}
    )
    respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Maria%20Silva").respond(
        200, json={"wikibase_item": "Q1"}
    )
    respx.get(WIKIDATA + "/wiki/Special:EntityData/Q1.json").respond(
        200, json={"entities": {"Q1": {}}}
    )
    async with httpx.AsyncClient() as client:
        result = await documented_family(client, PERSON)
    assert not result.found and result.source_url.endswith("Q1")


@respx.mock
def test_family_route_and_invalid_id():
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
        assert client.get("/politicians/camara/1/family").status_code == 200
        assert client.get("/politicians/camara/0/family").status_code == 422
