from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.assets import _divulga_president_assets, _json_money, _money, _rows, declared_assets
from app.main import app
from app.models import Politician


def archive(name: str, header: str, *rows: str) -> bytes:
    target = BytesIO()
    with ZipFile(target, "w") as zipped:
        zipped.writestr(name, (header + "\n" + "\n".join(rows)).encode("cp1252"))
        zipped.writestr("ignore.txt", b"x")
    return target.getvalue()


@respx.mock
async def test_declared_assets_matches_name_state_and_tse_identity():
    candidates = archive(
        "c.csv", "SQ_CANDIDATO;NM_CANDIDATO;SG_UF", "77;Maria da Silva;SP", "88;Maria da Silva;RJ"
    )
    goods = archive(
        "b.csv",
        "SQ_CANDIDATO;DS_TIPO_BEM_CANDIDATO;DS_BEM_CANDIDATO;VR_BEM_CANDIDATO",
        "77;Apartamento;Imóvel residencial;1.234,50",
        "77;Empresa;Quotas da empresa;inválido",
    )
    respx.get(
        "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip"
    ).respond(content=candidates)
    respx.get(
        "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2022.zip"
    ).respond(content=goods)
    person = Politician(id=1, name="Maria da Silva", party="X", state="SP", source_url="x")
    async with httpx.AsyncClient() as client:
        result = await declared_assets(client, person)
    assert result.available and result.total == 1234.50 and len(result.assets) == 2
    assert result.assets[0].company_url is None
    assert _money("") == 0

    respx.get(
        "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip"
    ).respond(content=candidates)
    respx.get(
        "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2024.zip"
    ).respond(content=goods)
    async with httpx.AsyncClient() as client:
        tse = await declared_assets(
            client, person.model_copy(update={"provider": "tse2024", "id": 77})
        )
    assert tse.election_year == 2024 and tse.available


def test_asset_reader_rejects_invalid_zip():
    with pytest.raises(ValueError):
        _rows(b"invalid")


@respx.mock
def test_asset_routes_and_invalid_id():
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
    respx.get(url__regex=r"https://cdn\.tse\.jus\.br/.+2022\.zip").respond(503)
    person = Politician(id=1, name="Maria", party="X", state="SP", source_url="x")
    async with httpx.AsyncClient() as client:
        result = await declared_assets(client, person)
    assert not result.available and "não pôde" in result.notice


@respx.mock
async def test_president_assets_use_election_year_and_civil_name():
    candidates = archive("c.csv", "SQ_CANDIDATO;NM_CANDIDATO;SG_UF", "99;JAIR MESSIAS BOLSONARO;BR")
    goods = archive(
        "b.csv",
        "SQ_CANDIDATO;DS_TIPO_BEM_CANDIDATO;DS_BEM_CANDIDATO;VR_BEM_CANDIDATO",
        "99;Casa;Imóvel;10,00",
    )
    respx.get(url__regex=r"https://cdn\.tse\.jus\.br/.+consulta_cand_2022\.zip").respond(
        content=candidates
    )
    respx.get(url__regex=r"https://cdn\.tse\.jus\.br/.+bem_candidato_2022\.zip").respond(
        content=goods
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
        result = await declared_assets(client, person)
    assert result.available and result.total == 300.5
    assert result.assets[0].description == "CDB"
    assert "DivulgaCandContas" in result.notice
    assert result.source_url.endswith("/280001607829/bens")
    assert _json_money("inválido") == 0


@respx.mock
async def test_lula_assets_fall_back_when_individual_service_fails():
    respx.get(url__regex=r"https://divulgacandcontas\.tse\.jus\.br/.+").respond(503)
    respx.get(url__regex=r"https://cdn\.tse\.jus\.br/.+2022\.zip").respond(503)
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
        result = await declared_assets(client, person)
    assert not result.available and result.election_year == 2022


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


async def test_president_without_open_asset_series_explains_limit():
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
    assert not result.available and result.election_year is None
    assert "formato aberto" in result.notice
