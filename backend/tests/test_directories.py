from datetime import UTC, datetime

import pytest
import respx
from fastapi.testclient import TestClient

from app.directories import MINISTRIES, SENATE, STJ
from app.main import app

BASE = "https://dadosabertos.camara.leg.br/api/v2/"
SENATOR = {
    "IdentificacaoParlamentar": {
        "CodigoParlamentar": "3",
        "NomeParlamentar": "João Silva",
        "NomeCompletoParlamentar": "João da Silva",
        "SiglaPartidoParlamentar": "ABC",
        "UfParlamentar": "SP",
        "EmailParlamentar": "joao@senado.leg.br",
        "UrlFotoParlamentar": "http://www.senado.leg.br/photo.jpg",
        "UrlPaginaParlamentar": "http://www25.senado.leg.br/perfil/3",
    },
    "Mandato": {"DescricaoParticipacao": "Titular"},
}
PERSON = """<h1 class="documentFirstHeading">Maria Silva</h1>
<div class="item">
<p class="autoridade">MINISTRA</p>
<img src="/photo.jpg">
<p class="email">E-mail: maria@gov.br</p>
<p class="telefone">Telefone: 123</p>
<div class="descricao_pessoa">Currículo da autoridade</div>
</div>"""
TREASURY_PERSON = MINISTRIES[2][1] + "/maria"
ROSTER = """<div class="clsMinistrosLinha">
<span class="clsMinistrosNome">
<a href="verCurriculoMinistro?parametro=1&cod_matriculamin=0001209">João Silva</a>
</span>
<span class="clsMinistrosNaturalidade">SP</span>
</div>"""
JUDICIAL_PERSON = (
    "https://www.stj.jus.br/web/verCurriculoMinistro?parametro=1&cod_matriculamin=0001209"
)
CURRICULUM = """<div class="curriculo0001209">
<img src="/photo.jpg">
<div class="clsMinistrosDiscursoItemDescricao">Formação</div>
<p>Direito</p>
<p>
<ul>
<li>Ministro desde 2020</li>
</ul>
</p>
<p>
</p>
</div>"""


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


def senate(items):
    respx.get(
        SENATOR["IdentificacaoParlamentar"]["UrlPaginaParlamentar"].replace("http://", "https://")
    ).respond(503)
    respx.get(
        f"https://www6g.senado.leg.br/transparencia/sen/3/?ano={datetime.now(UTC).year}"
    ).respond(503)
    respx.get(SENATE).respond(
        200, json={"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": items}}}
    )


def executive(person=PERSON, index=None):
    respx.get(MINISTRIES[1][1]).respond(200, text=person)
    respx.get(MINISTRIES[2][1]).respond(
        200,
        text=index
        or '<div id="content-core"><a href="' + TREASURY_PERSON + '">Maria Silva</a></div>',
    )
    respx.get(TREASURY_PERSON).respond(200, text=person)


@respx.mock
def test_autocomplete_limit_and_validation(client):
    respx.get(BASE + "deputados").respond(
        200,
        json={
            "dados": [
                {"id": i + 1, "nome": "Maria", "siglaPartido": "ABC", "siglaUf": "SP"}
                for i in range(12)
            ]
        },
    )
    assert len(client.get("/autocomplete?q=Maria").json()) == 8
    for path in ["/autocomplete?q=a", "/autocomplete?q=%20%20", "/search?q=Maria&provider=other"]:
        assert client.get(path).status_code == 422


@respx.mock
def test_senate_search_and_profile(client):
    senate([SENATOR])
    result = client.get("/autocomplete?q=joao&provider=senado").json()
    assert result[0]["role"] == "Senador(a)"
    assert result[0]["photo_url"].startswith("https://")
    assert client.get("/search?q=zz&provider=senado").json() == []
    assert client.get("/politicians/senado/3").json()["email"] == "joao@senado.leg.br"
    data = client.get("/politicians/senado/3/dashboard").json()
    assert "Participação no mandato: Titular" in str(data["sections"])
    assert data["metrics"][0]["group"] == "Perfil institucional"
    pdf = client.post("/reports/pdf", json=data)
    assert pdf.content.startswith(b"%PDF")
    assert "perfil-3.pdf" in pdf.headers["content-disposition"]
    assert client.get("/politicians/senado/99").status_code == 404


@respx.mock
def test_senate_missing_optional_fields(client):
    item = {
        "IdentificacaoParlamentar": {
            k: v
            for k, v in SENATOR["IdentificacaoParlamentar"].items()
            if k not in {"EmailParlamentar", "UrlFotoParlamentar", "NomeCompletoParlamentar"}
        }
    }
    senate([item])
    data = client.get("/politicians/senado/3/dashboard").json()
    assert data["politician"]["photo_url"] is None
    assert "Não informado" in str(data["sections"])
    senate([])
    assert client.get("/search?q=joao&provider=senado").json() == []


@respx.mock
def test_executive_current_profiles(client):
    executive()
    result = client.get("/search?q=maria&provider=executivo").json()
    assert len(result) == 2
    assert result[0]["power"] == "executivo"
    assert result[0]["email"] == "maria@gov.br"
    assert respx.calls[0].request.headers["accept"] == "text/html"
    assert result[1]["source_url"] == TREASURY_PERSON
    assert (
        client.get("/politicians/executivo/2/dashboard").json()["politician"]["name"]
        == "Maria Silva"
    )
    executive(
        PERSON.replace('<img src="/photo.jpg">', "").replace(
            '<p class="email">E-mail: maria@gov.br</p>', ""
        )
    )
    data = client.get("/politicians/executivo/1").json()
    assert data["photo_url"] is None and data["email"] is None


@pytest.mark.parametrize(
    "first,index",
    [
        ("<h1>captcha</h1>", None),
        (PERSON.replace('<h1 class="documentFirstHeading">Maria Silva</h1>', ""), None),
        (PERSON, "<div id='content-core'></div>"),
    ],
)
@respx.mock
def test_executive_invalid_source(client, first, index):
    executive(first, index)
    assert client.get("/search?q=maria&provider=executivo").status_code == 502


@respx.mock
def test_judiciary_profile(client):
    respx.get(STJ).respond(200, text=ROSTER)
    respx.get(JUDICIAL_PERSON).respond(200, text=CURRICULUM)
    result = client.get("/search?q=joao&provider=judiciario").json()
    assert result[0]["id"] == 1209
    assert result[0]["party"] == "Não se aplica"
    assert result[0]["photo_url"] is None
    data = client.get("/politicians/judiciario/1209/dashboard").json()
    assert data["politician"]["photo_url"] == "https://www.stj.jus.br/photo.jpg"
    assert "Ministro desde 2020" in str(data["sections"])
    latin = CURRICULUM.replace("Formação", "Formação Acadêmica")
    respx.get(JUDICIAL_PERSON).respond(
        200,
        content=latin.encode("iso-8859-1"),
        headers={"Content-Type": "text/html; charset=ISO-8859-1"},
    )
    assert "Formação Acadêmica" in str(
        client.get("/politicians/judiciario/1209/dashboard").json()["sections"]
    )
    respx.get(JUDICIAL_PERSON).respond(200, text=CURRICULUM.replace('<img src="/photo.jpg">', ""))
    assert client.get("/politicians/judiciario/1209").json()["photo_url"] is None


@pytest.mark.parametrize(
    "listing,curriculum",
    [
        ("captcha", CURRICULUM),
        ('<div class="clsMinistrosLinha"></div>', CURRICULUM),
        (ROSTER, "captcha"),
    ],
)
@respx.mock
def test_judiciary_invalid_source(client, listing, curriculum):
    respx.get(STJ).respond(200, text=listing)
    respx.get(JUDICIAL_PERSON).respond(200, text=curriculum)
    assert client.get("/politicians/judiciario/1209/dashboard").status_code == 502


@pytest.mark.parametrize(
    "provider,url", [("senado", SENATE), ("executivo", MINISTRIES[1][1]), ("judiciario", STJ)]
)
@respx.mock
def test_new_sources_unavailable(client, provider, url):
    respx.get(url).respond(503)
    assert client.get("/search", params={"q": "Maria", "provider": provider}).status_code == 502
