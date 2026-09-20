import json
from io import BytesIO
from unittest.mock import AsyncMock
from zipfile import ZipFile

import httpx
import pytest
import respx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.elections import ElectionProvider, published_2024_snapshot
from app.governors import SOURCE, STATES, GovernorProvider, decode_public
from app.main import app
from app.models import Politician
from app.universal_search import SOURCE_NAMES, universal_search


def governor_groups():
    return [
        {
            "categoria": "Governadores",
            "pessoas": [
                {
                    "nomeCompleto": "Carlos Roberto Massa Junior"
                    if uf == "PR"
                    else "Autoridade " + uf,
                    "municipio": "Capital - " + uf,
                    "cargo": "Governador",
                    "instituicao": "Governo " + uf,
                    "telefone": "123",
                    "situacaoCargo": "Interino" if uf == "RJ" else "",
                    "extra": None,
                    "semDataNascimento": False,
                }
                for uf in STATES
            ],
        }
    ]


@respx.mock
async def test_governors_all_states_and_aliases():
    groups = governor_groups()
    route = respx.get(SOURCE).respond(
        200, content=json.dumps(groups, ensure_ascii=False).encode("cp1252")
    )
    async with httpx.AsyncClient() as client:
        source = GovernorProvider(client)
        listing = await source.listing()
        assert {data.politician.state for data in listing} == set(STATES)
        assert len(listing) == 27
        person = (await source.search("ratinho"))[0]
        assert person.state == "PR" and person.power == "executivo"
        assert (await source.search("Autoridade AC"))[0].state == "AC"
        assert await source.search("Pessoa inexistente") == []
        assert (await source.get(33)).name == "Autoridade RJ"
        dashboard = await source.dashboard(33)
        assert dashboard.metrics[1].value == "Interino"
        assert dashboard.politician.party == "Não informado pela fonte"
        assert "extra" not in str(dashboard.sections[0])
        with pytest.raises(HTTPException):
            await source.get(99)
    assert route.calls[0].request.url.params["categoriaId"] == "18"
    assert decode_public("Órgão".encode("utf-8-sig")) == "Órgão"
    assert decode_public("Órgão".encode("cp1252")) == "Órgão"


@respx.mock
async def test_incomplete_governors_rejected():
    respx.get(SOURCE).respond(200, json=[])
    async with httpx.AsyncClient() as client:
        assert len(await GovernorProvider(client).listing()) == 27
    respx.get(SOURCE).respond(503)
    async with httpx.AsyncClient() as client:
        assert len(await GovernorProvider(client).listing()) == 27
    groups = governor_groups()
    groups[0]["pessoas"] = groups[0]["pessoas"][:1]
    respx.get(SOURCE).respond(200, json=groups)
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await GovernorProvider(client).listing()


def archive(brazil=True):
    data = BytesIO()
    text = (
        "SQ_CANDIDATO;NM_CANDIDATO;NM_URNA_CANDIDATO;DS_CARGO;SG_PART"
        "IDO;SG_UF;NM_UE;NR_CPF_CANDIDATO;DS_SITUACAO_CANDIDATURA;DS_GENERO;DS_COR_RACA\n1;M"
        "aria São;Maria;VEREADOR;ABC;SP;São "
        "Paulo;12345678900;APTO;FEMININO;PARDA\n2;João "
        "Silva;João;GOVERNADOR;DEF;RJ;Rio de "
        "Janeiro;98765432100;APTO;MASCULINO;BRANCA\n3;Ana;Ana;VEREADOR;ABC;SP;São "
        "Paulo;111;INAPTO;FEMININO;PRETA\n"
    )
    with ZipFile(data, "w") as z:
        z.writestr("README.txt", "Informações")
        z.writestr(
            "consulta_cand_2026_BRASIL.csv" if brazil else "consulta_cand_2026_SP.csv",
            text.encode("cp1252"),
        )
        if brazil:
            z.writestr("consulta_cand_2026_SP.csv", text.encode("cp1252"))
    return data.getvalue()


@respx.mock
async def test_election_search_and_internal_dashboard():
    async with httpx.AsyncClient() as client:
        source = ElectionProvider(client, 2026)
        respx.get(source.url).respond(200, content=archive())
        assert len(source.read(archive(False), "a")) == 3
        assert len(source.read(archive(), "a")) == 3
        assert source.read(archive(), "ninguém") == []
        assert (await source.search("maria sao"))[0].power == "legislativo"
        assert (await source.search("joao"))[0].party == "DEF"
        assert (await source.get(2)).power == "executivo"
        demographics = await source.demographics()
        assert demographics.total == 2
        assert demographics.sex_total == 2 and demographics.race_total == 2
        assert demographics.sex[0].value == 1
        assert {group.label for group in demographics.race} == {"Branca", "Parda"}
        empty_data = BytesIO()
        with ZipFile(empty_data, "w") as zipped:
            zipped.writestr(
                "consulta_cand_2026_BRASIL.csv",
                "SQ_CANDIDATO;DS_SITUACAO_CANDIDATURA;DS_GENERO;DS_COR_RACA\n".encode("cp1252"),
            )
        empty = source.read_demographics(empty_data.getvalue())
        assert empty.total == 0 and empty.sex == []
        dashboard = await source.dashboard(1)
        assert dashboard.year == "2026"
        assert "12345678900" not in dashboard.model_dump_json()
        assert "VEREADOR" in dashboard.model_dump_json()
        with pytest.raises(HTTPException):
            await source.dashboard(99)
        with pytest.raises(ValueError):
            source.read(b"arquivo quebrado", "Maria")
        with pytest.raises(ValueError):
            source.read_demographics(b"arquivo quebrado")


@respx.mock
async def test_demographics_uses_official_published_fallback_for_blocked_cdn():
    async with httpx.AsyncClient() as client:
        source = ElectionProvider(client, 2024)
        respx.get(source.url).respond(403)
        snapshot = await source.demographics()
        assert snapshot.sex_total == 456_310
        assert snapshot.race_total == 463_394
        assert snapshot.race[0].label == "Branca"
        source_2026 = ElectionProvider(client, 2026)
        respx.get(source_2026.url).respond(403)
        with pytest.raises(httpx.HTTPStatusError):
            await source_2026.demographics()
    assert published_2024_snapshot().sex[1].label == "Mulheres"


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("timeout"),
        ValueError("invalid"),
        KeyError("missing"),
        TypeError("invalid"),
    ],
)
async def test_universal_search_keeps_other_sources_and_reports_failures(error):
    person = Politician(
        id=1, name="Maria", party="ABC", state="SP", source_url="https://example.com"
    )
    providers = {key: AsyncMock() for key in SOURCE_NAMES}
    for source in providers.values():
        source.search.return_value = [person, person.model_copy(update={"id": 2, "name": "Zélia"})]
    providers["senado"].search.side_effect = error
    result = await universal_search(providers, "Maria")
    assert [p.name for p in result.items] == ["Maria", "Zélia"]
    assert result.sources[1].available is False
    assert result.sources[0].matches == 2
    assert len((await universal_search(providers, "Maria", 1)).items) == 1
    for source in providers.values():
        source.search.assert_awaited_with("Maria")


def test_universal_routes_validate_and_limit(monkeypatch):
    with TestClient(app) as client:
        assert client.get("/search/all?q=%20%20").status_code == 422
        assert client.get("/autocomplete/all?q=x").status_code == 422
        for key in SOURCE_NAMES:
            fake = AsyncMock()
            fake.search.return_value = [
                Politician(
                    id=i,
                    provider=key,
                    name="Maria",
                    party="ABC",
                    state="SP",
                    source_url="https://example.com",
                )
                for i in range(10)
            ]
            monkeypatch.setitem(app.state.providers, key, fake)
        assert len(client.get("/search/all?q=Maria").json()["items"]) == len(SOURCE_NAMES) * 10
        assert len(client.get("/autocomplete/all?q=Maria").json()["items"]) == 8
        assert all(
            source["available"] for source in client.get("/search/all?q=Maria").json()["sources"]
        )


def test_demographics_route(monkeypatch):
    with TestClient(app) as client:
        source = ElectionProvider(app.state.http_client, 2024)
        source.demographics = AsyncMock(return_value=source.read_demographics(archive()))
        monkeypatch.setitem(app.state.providers, "tse2024", source)
        response = client.get("/demographics?year=2024")
        assert response.status_code == 200 and response.json()["total"] == 2
        monkeypatch.setitem(app.state.providers, "tse2024", AsyncMock())
        assert client.get("/demographics?year=2024").status_code == 404
