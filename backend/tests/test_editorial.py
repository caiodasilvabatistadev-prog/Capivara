import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.directories import SENATE
from app.editorial import CATALOG, JudicialCase, context_for
from app.main import app
from app.models import Politician


@pytest.mark.parametrize(
    "status,final",
    [
        ("condenacao_definitiva", True),
        ("condenacao_recorrivel", False),
        ("em_andamento", False),
        ("absolvido", True),
        ("arquivado", True),
        ("anulado", False),
        ("pedido_rejeitado", False),
    ],
)
def test_supported_judicial_states(status, final):
    data = CATALOG[("senado", 6331)].cases[0].model_dump(mode="json")
    data.update(status=status, final_judgment=final)
    assert JudicialCase.model_validate(data).status == status


@pytest.mark.parametrize(
    "patch",
    [
        {"status": "condenacao_definitiva", "final_judgment": False},
        {"status": "em_andamento", "final_judgment": True},
        {"status": "condenacao_recorrivel", "final_judgment": True},
        {"status": "culpado"},
        {
            "official_source": {
                "publisher": "Jornal",
                "url": "https://example.com",
                "published_at": "2024-05-21",
            }
        },
    ],
)
def test_unproven_or_inconsistent_status_is_rejected(patch):
    data = CATALOG[("senado", 6331)].cases[0].model_dump(mode="json")
    data.update(patch)
    with pytest.raises(ValidationError):
        JudicialCase.model_validate(data)


def test_identity_and_missing_coverage():
    person = Politician(
        id=6331,
        provider="senado",
        name="Outra pessoa",
        party="ABC",
        state="SP",
        source_url="https://www.senado.leg.br",
    )
    data = context_for(person)
    assert data.reviewed_at is None and data.cases == []
    assert "não atesta" in data.notice


def test_lava_jato_record_states_annulment_and_sources():
    data = context_for(
        Politician(
            id=100,
            provider="presidentes",
            power="executivo",
            name="Luiz Inácio Lula da Silva",
            party="Não se aplica",
            state="Brasil",
            source_url="https://www.gov.br/planalto",
        )
    )
    case = data.cases[0]
    assert case.status == "anulado" and "não é absolvição" in case.summary
    assert case.official_source.url.host == "portal.stf.jus.br"
    assert case.journalism.url.host == "www.intercept.com.br"


@respx.mock
def test_context_of_reviewed_record():
    respx.get(SENATE).respond(
        200,
        json={
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {
                    "Parlamentar": [
                        {
                            "IdentificacaoParlamentar": {
                                "CodigoParlamentar": "6331",
                                "NomeParlamentar": "Sergio Moro",
                                "SiglaPartidoParlamentar": "ABC",
                                "UfParlamentar": "PR",
                                "UrlPaginaParlamentar": "https://www.senado.leg.br/perfil/6331",
                            }
                        }
                    ]
                }
            }
        },
    )
    with TestClient(app) as client:
        data = client.get("/politicians/senado/6331/context").json()
        assert data["cases"][0]["status"] == "pedido_rejeitado"
        assert data["cases"][0]["category"] == "eleitoral"
        assert data["cases"][0]["status_as_of"] == "2024-05-21"
        assert data["actions"][0]["stage"] == "aprovada"
        assert "tse.jus.br" in data["cases"][0]["official_source"]["url"]
        assert "exame.com" in data["cases"][0]["journalism"]["url"]


@respx.mock
def test_context_unknown_subject_and_upstream_errors():
    base = "https://dadosabertos.camara.leg.br/api/v2/deputados/1"
    with TestClient(app) as client:
        for path in ["/politicians/camara/0/context", "/politicians/other/1/context"]:
            assert client.get(path).status_code in {404, 422}
        respx.get(base).respond(
            200, json={"dados": {"id": 1, "nome": "Maria", "siglaPartido": "ABC", "siglaUf": "SP"}}
        )
        data = client.get("/politicians/camara/1/context").json()
        assert data["cases"] == [] and data["reviewed_at"] is None
        respx.get(base).respond(404)
        assert client.get("/politicians/camara/1/context").status_code == 404
        respx.get(base).mock(side_effect=httpx.ReadTimeout("timeout"))
        assert client.get("/politicians/camara/1/context").status_code == 502
