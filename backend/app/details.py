from datetime import UTC, datetime
from re import fullmatch

from bs4 import BeautifulSoup, Tag

from app.dashboard import Dashboard, Metric, ReportBlock, ReportSection, blocks, text


def add_metric(data: Dashboard, label: str, value: str, group: str, explanation: str) -> None:
    data.metrics = [item for item in data.metrics if item.label != label]
    data.metrics.append(Metric(label=label, value=value, group=group, explanation=explanation))


def add_section(data: Dashboard, title: str, node: Tag) -> None:
    data.sections.append(ReportSection(title=title, blocks=blocks(node)))


def complete_layout(data: Dashboard) -> Dashboard:
    legislative = data.politician.power == "legislativo"
    activity = {
        "legislativo": "Atividade legislativa",
        "executivo": "Atuação executiva",
        "judiciario": "Atividade judicial",
    }[data.politician.power]
    explanation = (
        "A fonte do perfil não fornece este indicador individual nesta consulta. "
        "Ausência de informação não significa zero."
    )
    for label, group in [
        ("Gastos individuais", "Gastos públicos"),
        ("Remuneração", "Recursos e benefícios"),
        ("Agenda e participação", "Presença e agenda"),
        ("Produção e resultados", activity),
    ]:
        add_metric(data, label, "Não disponível nesta consulta", group, explanation)
    add_metric(
        data,
        "Emendas parlamentares",
        "Não disponível nesta consulta" if legislative else "Não se aplica ao cargo",
        "Emendas ao orçamento",
        explanation
        if legislative
        else "Emendas de autoria parlamentar não são "
        "um indicador de atuação deste cargo. Execução de orçamento é uma informação distinta.",
    )
    data.notice = (
        "Dados oficiais do perfil e das fontes indicadas nas seções abaixo. "
        "A cobertura é parcial: indicadores sem fonte individual validada aparecem "
        "como não disponíveis. Não são zero e não permitem avaliar impacto ou qualidade."
    )
    return data


def senate_profile(data: Dashboard, html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    personal = soup.select_one(".dadosPessoais dl")
    if personal is None:
        raise ValueError("Perfil do Senado inválido")
    rows = [[text(term), text(term.find_next_sibling("dd"))] for term in personal.select("dt")]
    data.sections[0].blocks.append(ReportBlock(kind="table", text="Dados pessoais", rows=rows))
    for selector, title in [
        ("#accordion-chapa", "Mandato e suplentes"),
        ("#comissoes", "Participação em comissões"),
        ("#comissoesMPV", "Comissões de medidas provisórias"),
        ("#missoes", "Missões oficiais"),
        ("#accordion-biografia", "Biografia e mandatos anteriores"),
    ]:
        node = soup.select_one(selector)
        if node is not None:
            add_section(data, title, node)
    for selector, label in [
        ("#comissoes", "Participações atuais em comissões"),
        ("#missoes", "Missões listadas no perfil"),
    ]:
        table = soup.select_one(selector + " table")
        if table is not None:
            count = len(table.select("tbody tr"))
            add_metric(
                data,
                label,
                str(count),
                "Atividade legislativa",
                "Linhas publicadas no perfil oficial na data da consulta, "
                "incluindo participações como suplente. Não é produção anual nem presença.",
            )


def senate_resources(data: Dashboard, html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h1.sen-conteudo-interno")
    tables = soup.select("#conteudo_transparencia table")
    if heading is None or not tables:
        raise ValueError("Prestação de contas inválida")
    data.year = text(heading).removeprefix("Recursos Utilizados em ")
    for table in tables:
        caption = text(table.select_one("caption"))
        block = blocks(table)[0]
        block.text = caption
        data.sections.append(ReportSection(title=caption, blocks=[block]))
        rows = block.rows[1:]
        for row in rows:
            if len(row) != 2:
                continue
            label, value = row
            label = label.split("Obs.:", 1)[0].strip()
            group = "Recursos e benefícios"
            if "Cotas para Exercício" in caption:
                group = "Gastos públicos"
                if label == "Total":
                    label = (
                        "Cota parlamentar (CEAPS)"
                        if "não inclusos" not in caption
                        else "Gastos fora da CEAPS"
                    )
                value = "R$ " + value if fullmatch(r"-?\d[\d.]*,\d{2}", value) else value
            elif "funcionários" in caption:
                group = "Equipe e gabinete"
                if label not in {"Gabinete", "Escritório(s) de Apoio"}:
                    continue
            add_metric(
                data,
                label,
                value,
                group,
                "Informação publicada pelo Senado no ano "
                "indicado. Subtotais e categorias podem se sobrepor; não os somamos.",
            )
    data.metrics = [item for item in data.metrics if item.label != "Gastos individuais"]
    data.updates.extend(
        text(node) for node in soup.select(".accordion-inner span") if "Dados de" in text(node)
    )
    data.fetched_at = datetime.now(UTC)


def judicial_curriculum(data: Dashboard, curriculum: Tag) -> None:
    sections = curriculum.select(".clsMinistrosDiscursoItemDescricao")
    for heading in sections:
        content = []
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag):
                if "clsMinistrosDiscursoItemDescricao" in sibling.get_attribute_list("class"):
                    break
                content.extend(blocks(sibling))
        data.sections.append(ReportSection(title=text(heading), blocks=content))
        if text(heading) == "Funções Atuais":
            for index, block in enumerate(content):
                add_metric(
                    data,
                    "Função institucional " + str(index + 1),
                    block.text,
                    "Atividade judicial",
                    "Função descrita no currículo oficial; "
                    "não representa quantidade de decisões nem presença em sessões.",
                )
