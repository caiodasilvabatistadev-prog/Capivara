import asyncio
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.dashboard import ReportBlock, ReportSection, clean, text
from app.models import Politician

CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
SENADO = "https://legis.senado.leg.br/dadosabertos/votacao"
TRANSFEREGOV = "https://api.transferegov.gestao.gov.br/transferenciasespeciais"
CAMARA_SEARCH = "https://www.camara.leg.br/busca-api/api/v1/busca/proposicoes/_search"


def note(value: str) -> ReportBlock:
    return ReportBlock(kind="text", text=value)


def money(value: Decimal) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def plain_proposal(value: str) -> str:
    value = clean(value).rstrip(".")
    replacements = {
        "Dispõe sobre": "Cria regras sobre",
        "Institui": "Cria",
        "Altera a Lei": "Propõe mudança na Lei",
        "Acrescenta dispositivo à Lei": "Inclui uma nova regra na Lei",
    }
    for formal, simple in replacements.items():
        if value.startswith(formal):
            return simple + value[len(formal) :] + "."
    return value + ("." if value else "")


async def proposals(
    client: httpx.AsyncClient, person: Politician, year: int, reported: bool = False
) -> ReportSection:
    result = ReportSection(
        title="Propostas relatadas" if reported else "Propostas de sua autoria", blocks=[]
    )
    if person.provider != "camara":
        result.blocks = [
            note(
                "A lista detalhada de propostas está disponível nesta integração para "
                "deputados federais."
            )
        ]
        return result
    query = (
        f"relatores.ideCadastro: {person.id} AND "
        f"relatores.dataInicioRelator:[{year}-01-01 TO {year}-12-31]"
        if reported
        else f"autores.ideCadastro: {person.id} AND dataApresentacao:[{year}-01-01 TO {year}-12-31]"
    )
    hits: list[dict[str, Any]] = []
    page = 1
    while True:
        response = await client.post(
            CAMARA_SEARCH, params={"page": page}, json={"q": query, "pagina": page, "order": "data"}
        )
        response.raise_for_status()
        payload = response.json()["hits"]
        page_hits = payload["hits"]
        hits.extend(page_hits)
        if len(hits) >= int(payload["total"]["value"]) or not page_hits:
            break
        page += 1
    rows = []
    for item in hits:
        source = item.get("_source", {})
        proposal_id = int(item["_id"])
        description = clean(
            str(
                source.get("ementa")
                or source.get("explicacaoEmenta")
                or "Descrição não informada pela Câmara"
            )
        )
        rows.append(
            [
                str(source.get("dataApresentacao") or "Data não informada").split("T", 1)[0],
                str(source.get("titulo") or "Proposta sem identificação"),
                plain_proposal(description),
                description,
                str(
                    source.get("situacaoAtual")
                    or source.get("situacaoProposicao")
                    or "Situação não informada"
                ),
                f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={proposal_id}",
            ]
        )
    rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
    result.blocks = [
        note(
            f"Ano {year}. {len(rows)} proposta(s) "
            f"{'relatada(s)' if reported else 'de autoria'} encontrada(s). "
            f"Consulta em {datetime.now(UTC).isoformat()}."
        ),
        note(
            "A explicação simples é produzida a partir da descrição oficial, sem avaliar "
            "mérito, impacto ou chance de aprovação. A situação pode mudar depois da consulta."
        ),
        ReportBlock(
            kind="table",
            rows=[
                [
                    "Data",
                    "Identificação",
                    "Em palavras simples",
                    "Descrição oficial",
                    "Situação",
                    "Fonte oficial",
                ],
                *rows,
            ],
        ),
    ]
    return result


async def pix_amendments(
    client: httpx.AsyncClient, person: Politician, year: int
) -> tuple[list[list[str]], str]:
    query_name = "*".join(re.findall(r"[\wÀ-ÿ]+", person.name))
    response = await client.get(
        TRANSFEREGOV + "/plano_acao_especial",
        params={
            "nome_parlamentar_emenda_plano_acao": f"ilike.*{query_name}*",
            "ano_emenda_parlamentar_plano_acao": f"eq.{year}",
            "select": (
                "id_plano_acao,codigo_plano_acao,situacao_plano_acao,"
                "nome_beneficiario_plano_acao,uf_beneficiario_plano_acao,"
                "codigo_emenda_parlamentar_formatado_plano_acao,"
                "codigo_descricao_areas_politicas_publicas_plano_acao,"
                "descricao_programacao_orcamentaria_plano_acao,"
                "valor_custeio_plano_acao,valor_investimento_plano_acao"
            ),
            "order": "nome_beneficiario_plano_acao.asc",
            "limit": 1000,
        },
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    plans = response.json()
    semaphore = asyncio.Semaphore(8)

    async def row(plan: dict[str, object]) -> list[str]:
        async with semaphore:
            committed = await client.get(
                TRANSFEREGOV + "/empenho_especial",
                params={
                    "id_plano_acao": f"eq.{plan['id_plano_acao']}",
                    "select": "valor_empenho,descricao_situacao_empenho",
                    "limit": 1000,
                },
                headers={"Accept": "application/json"},
            )
            committed.raise_for_status()
        commitments = committed.json()
        committed_value = sum(
            (Decimal(str(item.get("valor_empenho") or 0)) for item in commitments), Decimal()
        )
        planned = Decimal(str(plan.get("valor_custeio_plano_acao") or 0)) + Decimal(
            str(plan.get("valor_investimento_plano_acao") or 0)
        )
        area = str(
            plan.get("codigo_descricao_areas_politicas_publicas_plano_acao")
            or plan.get("descricao_programacao_orcamentaria_plano_acao")
            or "Finalidade não informada"
        )
        beneficiary = str(plan.get("nome_beneficiario_plano_acao") or "Não informado")
        state = str(plan.get("uf_beneficiario_plano_acao") or "")
        code = str(
            plan.get("codigo_emenda_parlamentar_formatado_plano_acao")
            or plan.get("codigo_plano_acao")
            or ""
        )
        status = str(plan.get("situacao_plano_acao") or "Não informada")
        commitment_status = ", ".join(
            dict.fromkeys(
                str(item.get("descricao_situacao_empenho"))
                for item in commitments
                if item.get("descricao_situacao_empenho")
            )
        )
        return [
            "Emenda Pix · Transferência especial",
            beneficiary + (f" · {state}" if state else ""),
            area,
            money(planned),
            money(committed_value),
            "Não confirmado por esta consulta",
            f"{status}"
            + (f" · empenho: {commitment_status}" if commitment_status else "")
            + f" · {code}",
        ]

    rows = await asyncio.gather(*(row(plan) for plan in plans))
    note_text = (
        f"Emendas Pix: {len(rows)} plano(s) de ação encontrados no Transferegov para "
        f"{person.name} em {year}. Fonte: {TRANSFEREGOV}/plano_acao_especial. "
        "A modalidade oficial é Transferência Especial. O valor previsto soma custeio e "
        "investimento; o empenhado soma os registros ligados ao plano. Esta consulta não "
        "trata plano, empenho e pagamento como a mesma etapa."
    )
    return rows, note_text


async def amendments(client: httpx.AsyncClient, person: Politician, year: int) -> ReportSection:
    result = ReportSection(title="Destinos das emendas", blocks=[])
    if person.provider not in {"camara", "senado"}:
        result.blocks = [note("Autoria de emendas parlamentares não se aplica a este cargo.")]
        return result
    pix_rows, pix_note = await pix_amendments(client, person, year)
    url = f"https://www.camara.leg.br/deputados/{person.id}/todas-emendas"
    rows = [
        [
            "Modalidade",
            "Destino publicado",
            "Finalidade publicada",
            "Previsto ou autorizado",
            "Empenhado",
            "Pago",
            "Situação e identificação",
        ]
    ]
    total = 0
    for page in range(1, 21) if person.provider == "camara" else []:
        response = await client.get(
            url, params={"ano": year, "pagina": page}, headers={"Accept": "text/html"}
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        if not soup.select_one("#todas-emendas"):
            raise ValueError("Página de emendas inválida")
        counts = soup.select(".emendas-info-resultado strong")
        cards = soup.select(".emendas__item")
        total = int(text(counts[-1]).replace(".", "")) if counts else len(cards)
        for card in cards:
            amounts = {}
            for cell in card.select(".emendas-valores__item"):
                label = text(cell.select_one(".emendas-valores__titulo")).split()[0].rstrip(":")
                amounts[label] = text(cell.select_one(".emendas-valores__valor"))
            rows.append(
                [
                    "Emenda parlamentar",
                    text(card.select_one(".emendas__destino")),
                    text(card.select_one(".emendas__descricao")),
                    *[
                        amounts.get(key, "Não informado")
                        for key in ["Autorizado", "Empenhado", "Pago"]
                    ],
                    "Câmara dos Deputados",
                ]
            )
        if not cards or len(rows) - 1 >= total:
            break
    rows.extend(pix_rows)
    result.blocks = [
        note(
            f"Ano {year}. Câmara: consultadas {len(rows) - len(pix_rows) - 1} de "
            f"{total} destinações publicadas. Até 20 páginas. Consulta em "
            f"{datetime.now(UTC).isoformat()}."
        ),
        note(pix_note),
        note(
            "Órgão responsável não é necessariamente o beneficiário final. "
            "Localidades são reproduzidas como publicadas; esta página pode indicar "
            "apenas o estado. Autorizado é previsão; empenhado é reserva; pago é "
            "transferência, não comprova obra concluída ou serviço entregue. As "
            "etapas não são somadas. Detalhes por prefeitura, entidade recebedora e "
            "documento financeiro podem ter atualização e granularidade diferentes."
        ),
        ReportBlock(kind="table", rows=rows),
    ]
    return result


async def votes(client: httpx.AsyncClient, scope: str, person_id: int, days: int) -> ReportSection:
    result = ReportSection(title="Votos e assuntos em Plenário", blocks=[])
    if scope not in {"camara", "senado"}:
        result.blocks = [
            note(
                "Votos individuais em Plenário são indicadores parlamentares e não se "
                "aplicam a este cargo."
            )
        ]
        return result
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days)
    rows = [
        [
            "Data",
            "Identificação e objeto votado",
            "Contexto publicado",
            "Voto individual",
            "Fonte oficial",
        ]
    ]
    if scope == "senado":
        # Consulta cada ano envolvido, filtra localmente datas e identidade; sem endpoint legado.
        for year in range(start.year, end.year + 1):
            response = await client.get(
                SENADO,
                params={"ano": year, "codigoParlamentar": person_id},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            for item in response.json():
                date = item["dataSessao"]
                if not start.isoformat() <= date <= end.isoformat():
                    continue
                ballot = next(
                    (vote for vote in item["votos"] if int(vote["codigoParlamentar"]) == person_id),
                    None,
                )
                value = (
                    "Sem voto individual registrado"
                    if ballot is None
                    else ballot["siglaVotoParlamentar"]
                )
                if item["votacaoSecreta"] == "S":
                    value = "Voto secreto — posição individual não divulgada"
                rows.append(
                    [
                        date,
                        str(item["identificacao"]) + " — " + item["descricaoVotacao"],
                        item.get("ementa") or "Contexto não informado",
                        value,
                        f"{SENADO}?ano={year}&codigoParlamentar={person_id} | Sessão de votação "
                        f"{item['codigoSessaoVotacao']} / sequência {item['sequencialVotacao']}",
                    ]
                )
        result.blocks.append(
            note(
                "Fonte: API atual do Senado. O filtro de parlamentar pode retornar "
                "somente eventos com registro associado à pessoa; não constitui "
                "inventário de todas as votações ou ausências."
            )
        )
    else:
        response = await client.get(
            f"{CAMARA}/votacoes",
            params={
                "dataInicio": start.isoformat(),
                "dataFim": end.isoformat(),
                "idOrgao": 180,
                "itens": 100,
                "ordem": "DESC",
                "ordenarPor": "dataHoraRegistro",
            },
        )
        response.raise_for_status()
        payload = response.json()
        semaphore = asyncio.Semaphore(5)
        failures = []

        async def collect(item: dict[str, object]) -> list[str] | None:
            async with semaphore:
                url = f"{CAMARA}/votacoes/{item['id']}"
                try:
                    detail = await client.get(url)
                    detail.raise_for_status()
                    ballots = await client.get(url + "/votos")
                    ballots.raise_for_status()
                    records = ballots.json()["dados"]
                    if not records:
                        return None  # Não infere voto individual em votação simbólica.
                    value = next(
                        (
                            vote["tipoVoto"] or "Sem voto nominal registrado"
                            for vote in records
                            if int(vote["deputado_"]["id"]) == person_id
                        ),
                        "Sem voto nominal registrado",
                    )
                    data = detail.json()["dados"]
                    context = (
                        clean(
                            " | ".join(
                                dict.fromkeys(
                                    obj.get("ementa", "")
                                    for obj in data.get("objetosPossiveis", [])
                                )
                            )
                        )
                        or "Objeto e contexto não identificados pela fonte"
                    )
                    return [str(item["data"]), str(data["descricao"]), context, value, url]
                except httpx.HTTPError:
                    failures.append(str(item["id"]))
                    return None

        collected = await asyncio.gather(
            *(collect(item) for item in payload["dados"] if item["siglaOrgao"] == "PLEN")
        )
        rows.extend(row for row in collected if row is not None)
        result.blocks.append(
            note(
                f"Fonte: Câmara, até 100 eventos recentes de Plenário no intervalo. Apenas "
                f"listas com votos nominais são exibidas; não é levantamento completo. "
                f"Falhas de consulta: {len(failures)}. Objetos possíveis fornecem contexto "
                f"e não identificam necessariamente o texto exato deliberado; leia a "
                f"descrição da votação."
            )
        )
    rows[1:] = sorted(rows[1:], key=lambda row: row[0], reverse=True)
    result.blocks = [
        note(
            f"Período: {start.isoformat()} a {end.isoformat()}. Consulta em "
            f"{datetime.now(UTC).isoformat()}."
        ),
        note(
            "Sim e Não se referem ao objeto e à etapa desta votação, não à aprovação "
            "de toda a política pública. Abstenção, obstrução, presidência e voto "
            "secreto são preservados. Sem registro não significa falta: pode haver "
            "licença, período fora do mandato ou limitações da fonte. Não atribuímos "
            "intenção ou impacto ao voto."
        ),
        *result.blocks,
        ReportBlock(kind="table", rows=rows),
    ]
    return result
