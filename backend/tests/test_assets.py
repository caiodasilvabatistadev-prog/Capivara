import json
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.assets import (
    _divulga_president_assets,
    _hub_assets,
    _hub_payload,
    _hub_slug,
    _json_money,
    _lula_snapshot,
    _money,
    _rows,
    declared_assets,
)
from app.main import app
from app.models import Politician


def archive(name: str, header: str, *rows: str) -> bytes:
    target = BytesIO()
    with ZipFile(target, "w") as zipped:
        zipped.writestr(name, (header + "\n" + "\n".join(rows)).encode("cp1252"))
        zipped.writestr("ignore.txt", b"x")
    return target.getvalue()


def test_asset_archives_and_money_are_read_safely():
    candidates = archive(
        "c.csv", "SQ_CANDIDATO;NM_CANDIDATO;SG_UF", "77;Maria da Silva;SP", "88;Maria da Silva;RJ"
    )
    goods = archive(
        "b.csv",
        "SQ_CANDIDATO;DS_TIPO_BEM_CANDIDATO;DS_BEM_CANDIDATO;VR_BEM_CANDIDATO",
        "77;Apartamento;Imóvel residencial;1.234,50",
        "77;Empresa;Quotas da empresa;inválido",
    )
    assert _rows(candidates)[0]["SQ_CANDIDATO"] == "77"
    assert _rows(goods)[0]["DS_TIPO_BEM_CANDIDATO"] == "Apartamento"
    assert _money("1.234,50") == Decimal("1234.50")
    assert _money("") == 0
    assert _money("inválido") == 0


def test_asset_reader_rejects_invalid_zip():
    with pytest.raises(ValueError):
        _rows(b"invalid")


@respx.mock
def test_asset_routes_and_invalid_id():
    respx.get(url__regex=r"https://hubpolitico\.com\.br/.+").respond(404)
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").respond(
        200,
        json={
            "dados": {
                "id": 1,
                "ultimoStatus": {"nome": "Maria", "siglaPartido": "X", "siglaUf": "SP"},
            }
        },
    )
    empty = archive("x.csv", "SQ_CANDIDATO;NM_CANDIDATO;SG_UF")
    respx.get(url__regex=r"https://cdn\.tse\.jus\.br/.+2022\.zip").respond(content=empty)
    with TestClient(app) as client:
        assert client.get("/politicians/camara/1/assets").status_code == 200
        assert client.get("/politicians/camara/0/assets").status_code == 422


@respx.mock
async def test_assets_reports_official_source_unavailable():
    respx.get(url__regex=r"https://hubpolitico\.com\.br/.+").respond(503)
    respx.get(url__regex=r"https://cdn\.tse\.jus\.br/.+2022\.zip").respond(503)
    person = Politician(id=1, name="Maria", party="X", state="SP", source_url="x")
    async with httpx.AsyncClient() as client:
        result = await declared_assets(client, person)
    assert not result.available and "publicação alternativa" in result.notice
    assert "hubpolitico.com.br" in result.source_url


@respx.mock
async def test_assets_use_hubpolitico_tse_mirror_before_large_archives():
    payload = {
        "ano": 2022,
        "disponivel": True,
        "bens": [
            {"tipo": "Apartamento", "descricao": "Imóvel", "valor": 100},
            {"tipo": "Aplicação", "descricao": "CDB", "valor": 250.5},
            "inválido",
        ],
    }
    series = [
        {"ano": 2018, "patrimonio_total": 100},
        {"ano": 2022, "patrimonio_total": 150},
    ]
    chunk = json.dumps(
        [1, 'prefix"bens":' + json.dumps(payload) + ',"serie":' + json.dumps(series)]
    )
    page = f"<script>self.__next_f.push({chunk})</script>"
    route = respx.get(
        "https://hubpolitico.com.br/perfil/beneditadasilva/financeiro/patrimonio/2022"
    ).respond(200, text=page)
    person = Politician(id=1, name="Benedita da Silva", party="PT", state="RJ", source_url="x")
    async with httpx.AsyncClient() as client:
        result = await declared_assets(client, person)
    assert route.called and result.available and result.total == Decimal("350.5")
    assert result.assets[0].description == "CDB"
    assert result.growth_percentage == 50 and len(result.history) == 2
    assert result.verification == "single_source"
    assert result.source_checks[0].name == "HubPolítico"
    assert result.source_checks[0].status == "found"
    assert "HubPolítico" in result.notice
    assert _hub_slug("Benedita da Silva") == "beneditadasilva"

    payload_2024 = {**payload, "ano": 2024}
    chunk_2024 = json.dumps([1, 'prefix"bens":' + json.dumps(payload_2024)])
    tse_route = respx.get(
        "https://hubpolitico.com.br/perfil/beneditadasilva/financeiro/patrimonio/2024"
    ).respond(200, text=f"<script>self.__next_f.push({chunk_2024})</script>")
    async with httpx.AsyncClient() as client:
        tse = await declared_assets(client, person.model_copy(update={"provider": "tse2024"}))
    assert tse_route.called and tse.election_year == 2024


@respx.mock
async def test_hub_assets_rejects_unavailable_and_malformed_pages():
    endpoint = "https://hubpolitico.com.br/perfil/maria/financeiro/patrimonio/2022"
    route = respx.get(endpoint)
    person = Politician(id=1, name="Maria", party="X", state="SP", source_url="x")
    route.respond(503)
    async with httpx.AsyncClient() as client:
        assert await _hub_assets(client, person, 2022) is None
    route.respond(200, text='<script>self.__next_f.push("inválido")</script>')
    async with httpx.AsyncClient() as client:
        assert await _hub_assets(client, person, 2022) is None
    unavailable = json.dumps([1, 'x"bens":{"ano":2020,"disponivel":false,"bens":[]}'])
    route.respond(200, text=f"<script>self.__next_f.push({unavailable})</script>")
    async with httpx.AsyncClient() as client:
        assert await _hub_assets(client, person, 2022) is None
    assert _hub_payload('<script>self.__next_f.push([1, 2])</script>') is None
    assert _hub_payload('<script>self.__next_f.push([bad])</script>') is None
    malformed = json.dumps([1, 'x"bens":not-json'])
    assert _hub_payload(f"<script>self.__next_f.push({malformed})</script>") is None
    non_object = json.dumps([1, 'x"bens":[]'])
    assert _hub_payload(f"<script>self.__next_f.push({non_object})</script>") is None
    no_list = json.dumps([1, 'x"bens":{"ano":2022,"disponivel":true,"bens":{}}'])
    route.respond(200, text=f"<script>self.__next_f.push({no_list})</script>")
    async with httpx.AsyncClient() as client:
        assert await _hub_assets(client, person, 2022) is None


@respx.mock
async def test_president_assets_use_election_year_and_civil_name():
    payload = {
        "ano": 2022,
        "disponivel": True,
        "bens": [{"tipo": "Casa", "descricao": "Imóvel", "valor": 10}],
    }
    chunk = json.dumps([1, 'x"bens":' + json.dumps(payload)])
    respx.get(url__regex=r"https://hubpolitico\.com\.br/.+").respond(
        200, text=f"<script>self.__next_f.push({chunk})</script>"
    )
    person = Politician(
        id=107,
        provider="presidentes",
        power="executivo",
        name="Jair Bolsonaro",
        party="Não se aplica",
        state="Brasil",
        source_url="x",
    )
    async with httpx.AsyncClient() as client:
        result = await declared_assets(client, person)
    assert result.available and result.election_year == 2022 and result.total == 10


@respx.mock
async def test_lula_assets_use_individual_divulga_cand_contas():
    respx.get(
        "https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/buscar/"
        "2022/BR/2040602022/candidato/280001607829"
    ).respond(
        200,
        json={
            "nomeCompleto": "LUIZ INÁCIO LULA DA SILVA",
            "bens": [
                {
                    "descricaoDeTipoDeBem": "Apartamento",
                    "descricao": "Imóvel residencial",
                    "valor": 100.5,
                },
                {"descricaoDeTipoDeBem": "Aplicação", "descricao": "CDB", "valor": 200},
                "registro inválido",
            ],
        },
    )
    person = Politician(
        id=100,
        provider="presidentes",
        power="executivo",
        name="Luiz Inácio Lula da Silva",
        party="Não se aplica",
        state="Brasil",
        source_url="x",
    )
    async with httpx.AsyncClient() as client:
        result = await _divulga_president_assets(
            client, person, (2022, "2040602022", "280001607829")
        )
    assert result is not None
    assert result.available and result.total == 300.5
    assert result.assets[0].description == "CDB"
    assert "DivulgaCandContas" in result.notice
    assert result.source_url.endswith("/280001607829/bens")
    assert _json_money("inválido") == 0


@respx.mock
async def test_lula_assets_fall_back_when_individual_service_fails():
    result = _lula_snapshot()
    assert result.available and result.election_year == 2022
    assert len(result.assets) == 23
    assert result.total == _lula_snapshot().total == Decimal("7423725.78")
    assert "retrato da resposta oficial" in result.notice


@respx.mock
async def test_divulga_assets_rejects_error_invalid_json_and_wrong_person():
    endpoint = (
        "https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/buscar/"
        "2022/BR/election/candidato/candidate"
    )
    route = respx.get(endpoint)
    person = Politician(id=1, name="Maria", party="X", state="BR", source_url="x")
    route.respond(503)
    async with httpx.AsyncClient() as client:
        assert (
            await _divulga_president_assets(client, person, (2022, "election", "candidate")) is None
        )
    route.respond(200, content=b"not-json")
    async with httpx.AsyncClient() as client:
        assert (
            await _divulga_president_assets(client, person, (2022, "election", "candidate")) is None
        )
    route.respond(200, json={"nomeCompleto": "Outra pessoa"})
    async with httpx.AsyncClient() as client:
        assert (
            await _divulga_president_assets(client, person, (2022, "election", "candidate")) is None
        )


@respx.mock
async def test_president_without_open_asset_series_explains_limit():
    respx.get(url__regex=r"https://hubpolitico\.com\.br/.+").respond(404)
    person = Politician(
        id=101,
        provider="presidentes",
        power="executivo",
        name="José Sarney",
        party="Não se aplica",
        state="Brasil",
        source_url="x",
    )
    async with httpx.AsyncClient() as client:
        result = await declared_assets(client, person)
    assert not result.available and result.election_year == 2022
    assert "publicação alternativa" in result.notice
    assert result.source_checks[0].status == "not_found"
