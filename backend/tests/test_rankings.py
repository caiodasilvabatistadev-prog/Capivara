from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import app.rankings as module
from app.main import app
from app.models import Politician
from app.rankings import Entry, Ranking, absences, amendment_ranking, chamber_expenses, ordered


def archive(csv_text, year=2026):
    out = BytesIO()
    with ZipFile(out, "w") as file:
        file.writestr(f"Ano-{year}.csv", csv_text)
    return out.getvalue()


CSV = (
    "ideCadastro;txNomeParlamentar;vlrLiquido;numAno\n"
    "1;Maria;0.10;2026\n1;Maria;0.20;2026\n2;João;0.30;2026\n"
    ";Liderança;999;2026\n3;Ana;100;2025\n"
)
SENATE = [
    dict(id=1, ano=2026, codSenador=1, nomeSenador="Maria", valorReembolsado=0.1),
    dict(id=2, ano=2026, codSenador=1, nomeSenador="Maria", valorReembolsado=0.2),
    dict(id=2, ano=2026, codSenador=1, nomeSenador="Maria", valorReembolsado=0.2),
    dict(id=3, ano=2025, codSenador=2, nomeSenador="Outro", valorReembolsado=100),
]
PLENARY = """<main><div class="identificacao-deputado">Maria</div>
<span class="titulo-interno__ano">2026</span><section class="presencas__section">
<h4><a>Presença em Plenário</a></h4><ul>
<li class="presencas__data"><span class="presencas__label">Ausências justificadas</span>
<span class="presencas__qtd">2 dias</span></li>
<li class="presencas__data"><span class="presencas__label">Ausências não justificadas</span>
<span class="presencas__qtd">3 dias</span></li></ul></section></main>"""


def test_exact_money_and_ties_and_excluded_nonpersonal_rows():
    entries = ordered(chamber_expenses(archive(CSV), 2026))
    assert [item.name for item in entries] == ["João", "Maria"]
    assert [item.value for item in entries] == [Decimal("0.30"), Decimal("0.30")]
    assert [item.position for item in entries] == [1, 1]
    assert ordered([Entry(name=str(i), value=i) for i in range(11)])[-1].position == 10
    assert ordered([]) == []


def test_invalid_archive_columns_and_size_limit(monkeypatch):
    with pytest.raises(ValueError):
        chamber_expenses(archive("invalid\n1"), 2026)
    old = ZipFile.getinfo

    def large(self, name):
        result = old(self, name)
        result.file_size = 160_000_001
        return result

    monkeypatch.setattr(ZipFile, "getinfo", large)
    with pytest.raises(ValueError, match="limite"):
        chamber_expenses(archive(CSV), 2026)


@respx.mock
def test_rankings_endpoint_sources_and_limits():
    chamber = respx.get("https://www.camara.leg.br/cotas/Ano-2026.csv.zip").respond(
        200, content=archive(CSV)
    )
    senate = respx.get(
        "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/2026"
    ).respond(200, json=SENATE)
    with TestClient(app) as client:
        a = client.get("/rankings?metric=expenses&provider=camara&year=2026").json()
        b = client.get("/rankings?metric=expenses&provider=senado&year=2026").json()
        assert a["entries"][0]["value"] == "0.30"
        assert a["entries"][0]["photo_url"].endswith("/2.jpg")
        assert a["covered"] == 2
        assert b["entries"][0]["value"] == "0.3"
        assert b["covered"] == 1
        assert a["status"] == b["status"] == "ready"
        senate.respond(200, json=[])
        assert client.get("/rankings?provider=senado").json()["status"] == "unavailable"
        chamber.respond(200, content=b"not zip")
        assert client.get("/rankings").status_code == 502
        chamber.respond(503)
        assert client.get("/rankings").status_code == 502
        for query in ["provider=other", "metric=other", "year=2020", "year=2100"]:
            assert client.get("/rankings?" + query).status_code == 422
        for provider in ["executivo", "judiciario"]:
            for metric in ["expenses", "approved", "absences", "amendments"]:
                data = client.get(f"/rankings?provider={provider}&metric={metric}").json()
                assert data["status"] == "not_applicable" and data["entries"] == []
        assert client.get("/rankings?metric=approved").json()["status"] == "unavailable"
        amendments = client.get("/rankings?metric=amendments").json()
        assert amendments["status"] == "unavailable"
        assert "chave" in amendments["notice"]
        assert client.get("/rankings?metric=absences&year=2024").json()["status"] == "unavailable"
        assert (
            client.get("/rankings?provider=senado&metric=absences").json()["status"]
            == "unavailable"
        )
        for metric, year, total in [("party_fund", 2025, 19), ("election_fund", 2026, 30)]:
            data = client.get(f"/rankings?metric={metric}&year={year}").json()
            assert data["provider"] == "nacional"
            assert data["entries"][0]["name"] == "PL"
            assert data["source_url"].startswith("https://www.tse.jus.br/")
            assert data["total"] == total
            assert data["status"] == "ready"
        assert client.get("/rankings?metric=party_fund&year=2026").json()["entries"] == []
        assert client.get("/rankings?metric=election_fund&year=2025").json()["entries"] == []


@respx.mock
def test_current_chamber_absences_and_partial_coverage():
    year = datetime.now(UTC).year
    listing = respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados").respond(
        200,
        json={"dados": [dict(id=1, nome="Maria", siglaPartido="ABC", siglaUf="SP")], "links": []},
    )
    first = respx.get("https://www.camara.leg.br/deputados/1").respond(
        200, text=PLENARY.replace("2026", str(year))
    )
    with TestClient(app) as client:
        data = client.get(f"/rankings?metric=absences&year={year}").json()
        assert data["entries"][0]["value"] == "5"
        assert data["entries"][0]["detail"] == "2 justificadas · 3 não justificadas"
        assert data["entries"][0]["photo_url"] is None
        assert data["covered"] == data["total"] == 1 and data["status"] == "ready"
        listing.respond(
            200,
            json={
                "dados": [
                    dict(id=i, nome="Nome " + str(i), siglaPartido="ABC", siglaUf="SP")
                    for i in range(1, 4)
                ]
            },
        )
        respx.get("https://www.camara.leg.br/deputados/2").respond(503)
        respx.get("https://www.camara.leg.br/deputados/3").respond(
            200, text=PLENARY.replace("2026", "2020")
        )
        data = client.get(f"/rankings?metric=absences&year={year}").json()
        assert data["covered"] == 1 and data["total"] == 3 and data["status"] == "partial"
        first.respond(200, text="captcha")
        assert client.get(f"/rankings?metric=absences&year={year}").json()["entries"] == []


@pytest.mark.asyncio
async def test_absence_timeout_preserves_coverage_metadata(monkeypatch):
    class Deadline:
        async def __aenter__(self):
            raise TimeoutError

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(module.asyncio, "timeout", lambda seconds: Deadline())
    data = Ranking(provider="camara", metric="absences", year=2026, title="Faltas", notice="")
    person = Politician(
        id=1, name="Maria", party="ABC", state="SP", source_url="https://example.com"
    )
    async with httpx.AsyncClient() as client:
        result = await absences(client, [person], data)
    assert result.covered == 0 and result.total == 1 and result.entries == []


@respx.mock
async def test_amendment_ranking_uses_individual_committed_values():
    data = Ranking(provider="camara", metric="amendments", year=2026, title="Emendas", notice="")
    route = respx.get(module.TRANSPARENCY_API)
    route.side_effect = [
        httpx.Response(
            200,
            json=[
                {
                    "tipoEmenda": "Emenda Individual",
                    "nomeAutor": "Maria",
                    "valorEmpenhado": "R$ 1.234,50",
                },
                {
                    "tipoEmenda": "Emenda de Bancada",
                    "nomeAutor": "Bancada",
                    "valorEmpenhado": "999",
                },
                {"tipoEmenda": "Emenda Individual", "autor": "João", "valorEmpenhado": "- 100"},
                {"tipoEmenda": "Emenda Individual", "nomeAutor": "", "valorEmpenhado": "100"},
            ],
        ),
        httpx.Response(200, json=[]),
    ]
    async with httpx.AsyncClient() as client:
        result = await amendment_ranking(client, 2026, "token", data)
    assert [entry.name for entry in result.entries] == ["Maria", "João"]
    assert result.entries[0].value == Decimal("1234.50")
    assert result.entries[1].value == Decimal("-100")
    assert result.status == "ready" and result.covered == 2
    empty = Ranking(provider="camara", metric="amendments", year=2026, title="Emendas", notice="")
    assert (await amendment_ranking(httpx.AsyncClient(), 2026, "", empty)).status == "unavailable"
