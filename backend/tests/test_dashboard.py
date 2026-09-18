import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.dashboard import parse_dashboard
from app.main import app
from app.models import Politician
from app.pdf_report import make_pdf

PERSON = Politician(
    id=1, name="Maria", party="ABC", state="SP", source_url="https://www.camara.leg.br/deputados/1"
)
HTML = """<main>
<section class="identificacao-deputado"><h2>Maria</h2>
<a href="mailto:maria@example.org">maria@example.org</a>
<a>Biografia completa</a><ul><li>Telefone: 123</li></ul></section>
<section class="atividades-deputado"><p>2025 2026</p></section>
<section class="atuacao-deputado"><h2>Atuação <span class="titulo-interno__ano">2026</span></h2>
<div class="card"><h3 class="card-header__title">Propostas legislativas</h3>
<ul><li class="atuacao__item"><span class="atuacao__tipo">de sua autoria</span>
<a class="atuacao__quantidade">4</a></li></ul></div>
<div class="card"><div class="atuacao__item">Sem registro</div></div>
<section class="presencas__section"><h4><a>Plenário</a></h4>
<ul><li class="presencas__data"><span class="presencas__label">Presenças</span>
<span class="presencas__qtd">10 dias</span></li></ul></section>
<div class="atualizacao-secao">Atualizado em 18/09/2026</div></section>
<section class="cargos-deputado"><h2>Cargos</h2>Vice-líder</section>
<section class="emendas-deputado"><h2>Emendas</h2><p>Saúde</p>
<ul><li class="emendas__item"><p class="emendas__descricao">Saúde no estado</p>
<ul><li class="emendas-valores__item"><span class="emendas-valores__titulo">Autorizado</span>
<span class="emendas-valores__valor">R$ 100,00</span></li></ul></li></ul></section>
<section class="gastos-deputado"><h2>Gastos</h2>
<table id="percentualgastocotaparlamentar" aria-label="Cota">
<thead><tr><th>Tipo</th><th>R$</th></tr></thead>
<tbody><tr><td>Gasto</td><td>500,00</td></tr></tbody></table>
<table id="percentualgastoverbagabinete" aria-label="Gabinete"><tbody>
<tr><td>Gasto</td><td>200,00</td></tr></tbody></table></section>
<section class="recursos-deputado"><div class="beneficio"><h3>Salário mensal bruto
<a class="icone-ajuda">?</a></h3>
<span class="beneficio__info">R$ 46.366,19</span></div></section>
<section class="agenda-deputado"><h2>Agenda</h2><div class="g-agenda">Sem eventos</div></section>
<section class="noticias-deputado"><!-- Não incluir comentário --><h2>Notícias</h2>
<article><h3>Proposta de saúde</h3><span>Agência Câmara</span></article></section>
</main>"""


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


def test_extraction_and_missing_data():
    data = parse_dashboard(HTML, PERSON)
    assert data.year == "2026"
    assert data.politician.email == "maria@example.org"
    emenda = next(section for section in data.sections if section.title == "Emendas ao orçamento")
    assert any(
        block.rows == [["Etapa", "Valor"], ["Autorizado", "R$ 100,00"]] for block in emenda.blocks
    )
    assert len(data.sections) == 9
    assert data.metrics[0].value == "R$ 500,00"
    assert any(metric.value == "10 dias" for metric in data.metrics)
    assert any(metric.value == "4" for metric in data.metrics)
    assert any(metric.value == "Não informado" for metric in data.metrics)
    assert "Não incluir comentário" not in data.model_dump_json()
    assert "maria@example.org" in data.model_dump_json()
    assert "Biografia completa" not in data.model_dump_json()
    assert data.updates == ["Atualizado em 18/09/2026"]
    minimal = parse_dashboard(
        '<main><section class="identificacao-deputado">Maria</section></main>', PERSON
    )
    assert minimal.year is None
    assert all(metric.value == "Não informado" for metric in minimal.metrics)
    assert make_pdf(minimal).startswith(b"%PDF-")


@pytest.mark.parametrize("html", ["<html></html>", "<main></main>"])
def test_invalid_page(html):
    with pytest.raises(ValueError, match="Página oficial inválida"):
        parse_dashboard(html, PERSON)


@respx.mock
def test_dashboard_endpoint(client):
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").respond(
        200, json={"dados": {"id": 1, "nome": "Maria", "siglaPartido": "ABC", "siglaUf": "SP"}}
    )
    respx.get(PERSON.source_url).respond(200, text=HTML)
    response = client.get("/politicians/camara/1/dashboard")
    assert response.status_code == 200
    assert response.json()["politician"]["name"] == "Maria"
    assert response.json()["metrics"][0]["value"] == "R$ 500,00"


@pytest.mark.parametrize(
    "path", ["/politicians/camara/0/dashboard", "/politicians/other/1/dashboard"]
)
def test_dashboard_validation(client, path):
    assert client.get(path).status_code in (404, 422)


@pytest.mark.parametrize("status,body,expected", [(503, "", 502), (200, "invalid", 502)])
@respx.mock
def test_dashboard_upstream_error(client, status, body, expected):
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").respond(
        200, json={"dados": {"id": 1, "nome": "Maria", "siglaPartido": "ABC", "siglaUf": "SP"}}
    )
    respx.get(PERSON.source_url).mock(return_value=httpx.Response(status, text=body))
    assert client.get("/politicians/camara/1/dashboard").status_code == expected


def test_pdf_download_and_cors(client):
    data = parse_dashboard(HTML, PERSON)
    response = client.post("/reports/pdf", json=data.model_dump(mode="json"))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="deputado-1.pdf"'
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF-")
    assert client.post("/reports/pdf", json={}).status_code == 422
    preflight = client.options(
        "/reports/pdf",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
