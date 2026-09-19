from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.models import Politician
from app.parliament import (
    CAMARA,
    CAMARA_SEARCH,
    SENADO,
    TRANSFEREGOV,
    amendments,
    plain_proposal,
    proposals,
    votes,
)

PERSON = Politician(
    id=1,
    provider="camara",
    name="Maria",
    party="ABC",
    state="SP",
    source_url="https://www.camara.leg.br/deputados/1",
)


def html(description="Saúde no Ceará", total=2, card=True):
    summary = (
        f"<p "
        f'class="emendas-info-resultado"><strong>1</strong><strong>1</strong><strong>{total}</strong></p>'
        if total
        else ""
    )
    content = (
        f'<li class="emendas__item"><p class="emendas__destino">Fundo Nacional '
        f'de Saúde</p><p class="emendas__descricao">{description}</p><li '
        f'class="emendas-valores__item"><span '
        f'class="emendas-valores__titulo">Pago: ?</span><span '
        f'class="emendas-valores__valor">R$ 0,00</span></li></li>'
        if card
        else ""
    )
    return '<div id="todas-emendas">' + summary + "<ul>" + content + "</ul></div>"


@respx.mock
async def test_amendment_pages_unknown_and_paid_zero():
    plans = respx.get(TRANSFEREGOV + "/plano_acao_especial").respond(200, json=[])
    route = respx.get("https://www.camara.leg.br/deputados/1/todas-emendas").mock(
        side_effect=[
            httpx.Response(200, text=html()),
            httpx.Response(200, text=html("Educação no Ceará")),
        ]
    )
    async with httpx.AsyncClient() as client:
        section = await amendments(client, PERSON, 2026)
        rows = section.blocks[-1].rows
        assert len(rows) == 3 and rows[1][3] == "Não informado" and rows[1][-2] == "R$ 0,00"
        assert "2 de 2" in section.blocks[0].text
        assert route.calls[1].request.url.params["pagina"] == "2"
        route.mock(return_value=httpx.Response(200, text=html(total=0, card=False)))
        assert len((await amendments(client, PERSON, 2026)).blocks[-1].rows) == 1
        route.mock(return_value=httpx.Response(200, text="<html/>"))
        with pytest.raises(ValueError):
            await amendments(client, PERSON, 2026)
        senate = PERSON.model_copy(update={"provider": "senado"})
        assert "Emendas Pix" in (await amendments(client, senate, 2026)).blocks[1].text
        executive = PERSON.model_copy(update={"provider": "executivo"})
        assert "não se aplica" in (await amendments(client, executive, 2026)).blocks[0].text
        assert plans.called


@respx.mock
async def test_amendment_page_limit_is_explicitly_partial():
    respx.get(TRANSFEREGOV + "/plano_acao_especial").respond(200, json=[])
    respx.get("https://www.camara.leg.br/deputados/1/todas-emendas").mock(
        side_effect=lambda request: httpx.Response(
            200, text=html("Destino " + request.url.params["pagina"], total=25)
        )
    )
    async with httpx.AsyncClient() as client:
        section = await amendments(client, PERSON, 2026)
        assert "20 de 25" in section.blocks[0].text


@respx.mock
async def test_pix_amendments_include_beneficiary_values_and_commitment():
    plan = {
        "id_plano_acao": 9,
        "codigo_plano_acao": "0903",
        "situacao_plano_acao": "CIENTE",
        "nome_beneficiario_plano_acao": "Município de Exemplo",
        "uf_beneficiario_plano_acao": "SP",
        "codigo_emenda_parlamentar_formatado_plano_acao": "20260001-MARIA",
        "codigo_descricao_areas_politicas_publicas_plano_acao": "Saúde",
        "descricao_programacao_orcamentaria_plano_acao": None,
        "valor_custeio_plano_acao": 100,
        "valor_investimento_plano_acao": 200,
    }
    respx.get(TRANSFEREGOV + "/plano_acao_especial").respond(200, json=[plan])
    respx.get(TRANSFEREGOV + "/empenho_especial").respond(
        200,
        json=[
            {"valor_empenho": 150, "descricao_situacao_empenho": "Enviado"},
            {"valor_empenho": None, "descricao_situacao_empenho": "Enviado"},
        ],
    )
    respx.get("https://www.camara.leg.br/deputados/1/todas-emendas").respond(
        200, text=html(total=0, card=False)
    )
    async with httpx.AsyncClient() as client:
        section = await amendments(client, PERSON, 2026)
    row = section.blocks[-1].rows[1]
    assert row[:5] == [
        "Emenda Pix · Transferência especial",
        "Município de Exemplo · SP",
        "Saúde",
        "R$ 300,00",
        "R$ 150,00",
    ]
    assert "empenho: Enviado" in row[-1]


@respx.mock
async def test_authored_proposals_include_simple_and_official_text():
    respx.post(CAMARA_SEARCH).respond(
        200,
        json={
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "7",
                        "_source": {
                            "titulo": "PL 10/2026",
                            "ementa": "Dispõe sobre atendimento em hospitais.",
                            "dataApresentacao": "2026-03-02T10:00",
                            "situacaoAtual": "Aguardando parecer",
                        },
                    }
                ],
            }
        },
    )
    async with httpx.AsyncClient() as client:
        rows = (await proposals(client, PERSON, 2026)).blocks[-1].rows
        assert rows[1][1:5] == [
            "PL 10/2026",
            "Cria regras sobre atendimento em hospitais.",
            "Dispõe sobre atendimento em hospitais.",
            "Aguardando parecer",
        ]
        assert (
            "disponível"
            in (await proposals(client, PERSON.model_copy(update={"provider": "senado"}), 2026))
            .blocks[0]
            .text
        )
        reported = await proposals(client, PERSON, 2026, True)
        assert reported.title == "Propostas relatadas"
        assert "relatores.ideCadastro" in respx.calls[-1].request.content.decode()


@pytest.mark.parametrize(
    ("formal", "simple"),
    [
        ("Institui o programa.", "Cria o programa."),
        ("Altera a Lei 1.", "Propõe mudança na Lei 1."),
        ("Acrescenta dispositivo à Lei 2.", "Inclui uma nova regra na Lei 2."),
        ("Autoriza atendimento.", "Autoriza atendimento."),
        ("", ""),
    ],
)
def test_plain_proposal_variants(formal, simple):
    assert plain_proposal(formal) == simple


@respx.mock
async def test_authored_proposals_paginate_and_keep_missing_detail_explicit():
    first = [{"_id": str(index), "_source": {"ementa": None}} for index in range(20)]
    second = [{"_id": "20", "_source": {"explicacaoEmenta": "Institui atendimento."}}]
    respx.post(CAMARA_SEARCH).mock(
        side_effect=[
            httpx.Response(200, json={"hits": {"total": {"value": 21}, "hits": first}}),
            httpx.Response(200, json={"hits": {"total": {"value": 21}, "hits": second}}),
        ]
    )
    async with httpx.AsyncClient() as client:
        section = await proposals(client, PERSON, 2026)
    assert len(section.blocks[-1].rows) == 22
    assert section.blocks[-1].rows[1][0] == "Data não informada"


@respx.mock
async def test_chamber_nominal_votes_missing_record_symbolic_and_failure():
    today = datetime.now(UTC).date().isoformat()
    events = [{"id": str(n), "data": today, "siglaOrgao": "PLEN"} for n in range(4)] + [
        {"id": "commission", "siglaOrgao": "CCJC"}
    ]
    respx.get(CAMARA + "/votacoes").mock(return_value=httpx.Response(200, json={"dados": events}))
    for n in range(4):
        respx.get(CAMARA + f"/votacoes/{n}").mock(
            return_value=httpx.Response(503)
            if n == 3
            else httpx.Response(
                200,
                json={
                    "dados": {
                        "descricao": "Votação da emenda de saúde",
                        "objetosPossiveis": [{"ementa": "Saúde"}, {"ementa": "Saúde"}]
                        if n == 0
                        else [],
                    }
                },
            )
        )
        if n < 3:
            records = (
                []
                if n == 2
                else [
                    {
                        "tipoVoto": "Sim" if n == 0 else "Não",
                        "deputado_": {"id": 1 if n == 0 else 2},
                    }
                ]
            )
            respx.get(CAMARA + f"/votacoes/{n}/votos").mock(
                return_value=httpx.Response(200, json={"dados": records})
            )
    async with httpx.AsyncClient() as client:
        section = await votes(client, "camara", 1, 90)
        rows = section.blocks[-1].rows
        assert len(rows) == 3 and rows[1][3] == "Sim" and rows[1][2] == "Saúde"
        assert rows[2][3] == "Sem voto nominal registrado"
        assert "Falhas de consulta: 1" in section.blocks[2].text
        assert "não se aplicam" in (await votes(client, "judiciario", 1, 90)).blocks[0].text


@respx.mock
async def test_senate_current_api_secret_identity_and_interval():
    now = datetime.now(UTC).date()

    def record(code, date, secret="N", ballot=True):
        return {
            "dataSessao": date,
            "identificacao": "PL 1/2026",
            "descricaoVotacao": "Emenda sobre ensino",
            "ementa": "Educação",
            "votos": [{"codigoParlamentar": 1, "siglaVotoParlamentar": "Não"}] if ballot else [],
            "votacaoSecreta": secret,
            "codigoSessaoVotacao": code,
            "sequencialVotacao": 1,
        }

    entries = [
        record(1, now.isoformat()),
        record(2, now.isoformat(), "S"),
        record(3, now.isoformat(), ballot=False),
        record(4, (now - timedelta(days=500)).isoformat()),
    ]
    respx.get(SENADO).mock(return_value=httpx.Response(200, json=entries))
    async with httpx.AsyncClient() as client:
        rows = (await votes(client, "senado", 1, 30)).blocks[-1].rows
        assert len(rows) == 4 and rows[1][3] == "Não"
        assert rows[2][3] == "Voto secreto — posição individual não divulgada"
        assert rows[3][3] == "Sem voto individual registrado"


@respx.mock
def test_routes_identity_validation_and_pdf():
    respx.get(TRANSFEREGOV + "/plano_acao_especial").respond(200, json=[])
    respx.get(CAMARA + "/deputados/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "dados": {
                    "id": 1,
                    "ultimoStatus": {"nome": "Maria", "siglaPartido": "X", "siglaUf": "SP"},
                }
            },
        )
    )
    respx.get("https://www.camara.leg.br/deputados/1/todas-emendas").mock(
        return_value=httpx.Response(200, text=html(total=0, card=False))
    )
    respx.get(CAMARA + "/votacoes").mock(return_value=httpx.Response(200, json={"dados": []}))
    with TestClient(app) as client:
        assert client.get("/politicians/camara/1/amendments").status_code == 200
        assert client.get("/politicians/camara/1/votes").status_code == 200
        respx.post(CAMARA_SEARCH).respond(200, json={"hits": {"total": {"value": 0}, "hits": []}})
        assert client.get("/politicians/camara/1/proposals").status_code == 200
        for path in ["amendments", "votes", "proposals"]:
            assert client.get("/politicians/camara/0/" + path).status_code == 422
            assert client.get("/politicians/unknown/1/" + path).status_code == 404
        assert client.get("/politicians/camara/1/votes?days=366").status_code == 422
        assert client.get("/politicians/camara/1/amendments?year=1900").status_code == 422


@respx.mock
async def test_chamber_null_ballot_is_unknown_not_against():
    respx.get(CAMARA + "/votacoes").mock(
        return_value=httpx.Response(
            200, json={"dados": [{"id": "null", "siglaOrgao": "PLEN", "data": "2026-09-01"}]}
        )
    )
    respx.get(CAMARA + "/votacoes/null").mock(
        return_value=httpx.Response(
            200, json={"dados": {"descricao": "Objeto votado", "objetosPossiveis": []}}
        )
    )
    respx.get(CAMARA + "/votacoes/null/votos").mock(
        return_value=httpx.Response(
            200, json={"dados": [{"deputado_": {"id": 1}, "tipoVoto": None}]}
        )
    )
    async with httpx.AsyncClient() as client:
        rows = (await votes(client, "camara", 1, 90)).blocks[-1].rows
        assert rows[1][3] == "Sem voto nominal registrado"
