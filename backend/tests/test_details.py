from datetime import UTC, datetime

import httpx
import pytest
import respx
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.details import judicial_curriculum, senate_profile, senate_resources
from app.directories import SENATE, profile
from app.main import app
from app.models import Politician

PERSON = Politician(
    id=3,
    provider="senado",
    name="João Silva",
    party="ABC",
    state="SP",
    source_url="https://www25.senado.leg.br/perfil/3",
)
PROFILE = """<div class="dadosPessoais"><dl><dt>Nome civil</dt><dd>João Silva</dd>
<dt>Telefone</dt><dd>123</dd></dl></div>
<div id="accordion-chapa"><p>Titular e suplentes</p></div>
<div id="comissoes"><table><thead><tr><th>Comissão</th></tr></thead><tbody>
<tr><td>Comissão de teste</td></tr></tbody></table></div>
<div id="comissoesMPV"><p>Medida provisória</p></div>
<div id="missoes"><table><tbody><tr><td>Missão de teste</td></tr></tbody></table></div>
<div id="accordion-biografia"><p>Mandato de teste</p></div>"""


def table(caption, rows):
    return (
        "<table><caption>"
        + caption
        + "</caption><tr><th>Recurso</th><th>Valor</th></tr>"
        + rows
        + "</table>"
    )


RESOURCES = (
    '<h1 class="sen-conteudo-interno">Recursos Utilizados em 2026</h1>'
    '<div id="conteudo_transparencia">'
    + table(
        "Valores de Cotas para Exercício da Atividade Parlamentar",
        "<tr><td>Passagens</td><td>100,00</td></tr><tr><td>Total</td><td>100,00</td></tr>",
    )
    + table(
        "Valores de Gastos não inclusos nas Cotas para Exercício da Atividade Parlamentar",
        "<tr><td>Total</td><td>25,00</td></tr><tr><td>Combustíveis</td><td>consulte</td></tr>",
    )
    + table("Uso de Benefícios", "<tr><td>Auxílio-Moradia</td><td>Não utilizou</td></tr>")
    + table(
        "Quantidade de funcionários por local e vínculo",
        "<tr><td>Gabinete</td><td>2 pessoa(s)</td></tr>"
        "<tr><td>Comissionados</td><td>2 pessoa(s)</td></tr>",
    )
    + table("Outros", '<tr><td colspan="2">Nota sem quantidade</td></tr>')
    + '</div><div class="accordion-inner"><span>Sistema Cotas - Dados de 18/09/2026</span>'
    "<span>Nota</span></div>"
)


@respx.mock
def test_senate_dashboard_enrichment_and_pdf():
    info = {
        "CodigoParlamentar": "3",
        "NomeParlamentar": PERSON.name,
        "SiglaPartidoParlamentar": "ABC",
        "UfParlamentar": "SP",
        "UrlPaginaParlamentar": PERSON.source_url,
    }
    respx.get(SENATE).respond(
        200,
        json={
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {"Parlamentar": [{"IdentificacaoParlamentar": info}]}
            }
        },
    )
    respx.get(PERSON.source_url).respond(200, text=PROFILE)
    money = respx.get(
        f"https://www6g.senado.leg.br/transparencia/sen/3/?ano={datetime.now(UTC).year}"
    ).respond(200, text=RESOURCES)
    with TestClient(app) as client:
        data = client.get("/politicians/senado/3/dashboard").json()
        metrics = {item["label"]: item["value"] for item in data["metrics"]}
        assert metrics["Cota parlamentar (CEAPS)"] == "R$ 100,00"
        assert metrics["Gastos fora da CEAPS"] == "R$ 25,00"
        assert metrics["Auxílio-Moradia"] == "Não utilizou"
        assert metrics["Gabinete"] == "2 pessoa(s)"
        assert "Comissionados" not in metrics
        assert metrics["Combustíveis"] == "consulte"
        assert metrics["Participações atuais em comissões"] == "1"
        assert metrics["Missões listadas no perfil"] == "1"
        assert "Gastos individuais" not in metrics
        assert data["year"] == "2026"
        assert len(data["sections"]) >= 10
        assert "Consultada" in str(data["sections"][-1])
        assert data["updates"] == ["Sistema Cotas - Dados de 18/09/2026"]
        assert client.post("/reports/pdf", json=data).content.startswith(b"%PDF")
        money.mock(side_effect=httpx.ReadTimeout("timeout"))
        respx.get(PERSON.source_url).respond(200, text="captcha")
        partial = client.get("/politicians/senado/3/dashboard").json()
        assert partial["year"] is None
        assert "Indisponível" in str(partial["sections"][-1])


def test_optional_senate_sections_remain_unavailable():
    data = profile(PERSON, ["Perfil"])
    senate_profile(data, '<div class="dadosPessoais"><dl><dt>E-mail</dt></dl></div>')
    assert "Não informado" in str(data.sections)
    assert len(data.sections) == 1


@pytest.mark.parametrize(
    "html",
    [
        "captcha",
        '<div id="conteudo_transparencia"><table></table></div>',
        '<h1 class="sen-conteudo-interno">Recursos</h1>',
    ],
)
def test_invalid_financial_page_never_implies_zero(html):
    data = profile(PERSON, [])
    with pytest.raises(ValueError):
        senate_resources(data, html)
    assert data.year is None
    assert data.metrics[2].value == "Não disponível nesta consulta"


def test_judicial_functions_and_curriculum_sections():
    data = profile(PERSON.model_copy(update={"provider": "judiciario", "power": "judiciario"}), [])
    soup = BeautifulSoup(
        """<div><div class="clsMinistrosDiscursoItemDescricao">Funções Atuais</div>
Texto livre<p>Integra uma turma</p><hr><div class="clsMinistrosDiscursoItemDescricao">Formação</div>
<p>Curso de direito</p></div>""",
        "html.parser",
    )
    judicial_curriculum(data, soup.div)
    assert {s.title for s in data.sections} >= {"Funções Atuais", "Formação"}
    assert any(m.value == "Integra uma turma" for m in data.metrics)
    assert any(m.value == "Não se aplica ao cargo" for m in data.metrics)
