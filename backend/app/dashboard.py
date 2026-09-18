from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag
from bs4.element import Comment, NavigableString
from pydantic import BaseModel

from app.models import Politician


class Metric(BaseModel):
    label: str
    value: str
    group: str
    explanation: str


class ReportBlock(BaseModel):
    kind: str
    text: str = ""
    rows: list[list[str]] = []


class ReportSection(BaseModel):
    title: str
    blocks: list[ReportBlock]


class Dashboard(BaseModel):
    politician: Politician
    year: str | None
    fetched_at: datetime
    updates: list[str]
    metrics: list[Metric]
    sections: list[ReportSection]
    notice: str = (
        "Dados da página principal da Câmara, no período indicado. "
        "As quantidades não avaliam a qualidade ou o impacto do mandato. "
        "Não informado é diferente de zero. Páginas de detalhamento não estão incluídas."
    )


def clean(value: str) -> str:
    return " ".join(value.split())


def text(node: Tag | None) -> str:
    return clean(node.get_text(" ", strip=True)) if node else "Não informado"


def blocks(node: Tag) -> list[ReportBlock]:
    if "emendas__item" in node.get_attribute_list("class"):
        rows = [["Etapa", "Valor"]]
        for item in node.select(".emendas-valores__item"):
            rows.append(
                [
                    text(item.select_one(".emendas-valores__titulo")),
                    text(item.select_one(".emendas-valores__valor")),
                ]
            )
        return [
            ReportBlock(
                kind="table",
                text="Emenda: " + text(node.select_one(".emendas__descricao")),
                rows=rows,
            )
        ]
    if node.name in ("h2", "h3", "h4"):
        return [ReportBlock(kind="heading", text=text(node))]
    if node.name == "table":
        rows = [[text(cell) for cell in row.select("th,td")] for row in node.select("tr")]
        return [ReportBlock(kind="table", text=str(node.get("aria-label", "")), rows=rows)]
    atomic = {"beneficio__info", "atualizacao-secao", "atuacao__item", "g-agenda"}
    if (node.name in ("p", "li") and not node.find(["ul", "ol", "table", "h3", "p"])) or (
        atomic.intersection(node.get_attribute_list("class"))
    ):
        return [ReportBlock(kind="text", text=text(node))]
    result: list[ReportBlock] = []
    for child in node.children:
        if isinstance(child, Tag):
            result.extend(blocks(child))
        elif (
            isinstance(child, NavigableString)
            and not isinstance(child, Comment)
            and clean(str(child))
        ):
            result.append(ReportBlock(kind="text", text=clean(str(child))))
    return result


def parse_dashboard(html: str, politician: Politician) -> Dashboard:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main")
    if not main or not main.select_one(".identificacao-deputado"):
        raise ValueError("Página oficial inválida")
    email = main.select_one('.identificacao-deputado a[href^="mailto:"]')
    if email:
        politician = politician.model_copy(update={"email": text(email)})
    updates = [text(item) for item in main.select(".atualizacao-secao")]
    year_node = main.select_one(".titulo-interno__ano")
    metrics: list[Metric] = []
    for selector, label in (
        ("#percentualgastocotaparlamentar", "Cota parlamentar"),
        ("#percentualgastoverbagabinete", "Verba de gabinete"),
    ):
        amount = main.select_one(f"{selector} tbody tr td:nth-of-type(2)")
        metrics.append(
            Metric(
                label=label,
                value=f"R$ {text(amount)}" if amount else "Não informado",
                group="Gastos públicos",
                explanation="Total gasto no ano indicado pela fonte.",
            )
        )
    for card in main.select(".card"):
        title = card.select_one(".card-header__title")
        for item in card.select(".atuacao__item"):
            quantity = item.select_one(".atuacao__quantidade")
            metrics.append(
                Metric(
                    label=(
                        f"{text(title).replace(' ?', '')} - "
                        f"{text(item.select_one('.atuacao__tipo'))}"
                    ),
                    value=text(quantity),
                    group="Atividade legislativa",
                    explanation="Quantidade registrada pela Câmara no ano indicado.",
                )
            )
    for section in main.select(".presencas__section"):
        title = section.select_one("h4 > a")
        for item in section.select("li.presencas__data"):
            metrics.append(
                Metric(
                    label=f"{text(title)} - {text(item.select_one('.presencas__label'))}",
                    value=text(item.select_one(".presencas__qtd")),
                    group="Presença",
                    explanation=(
                        "Plenário conta dias; comissões contam reuniões. Não somamos os dois."
                    ),
                )
            )
    for item in main.select(".beneficio"):
        heading = item.select_one("h3")
        metrics.append(
            Metric(
                label=text(heading).replace(" ?", ""),
                value=text(item.select_one(".beneficio__info")),
                group="Recursos e benefícios",
                explanation="Informação publicada pela Câmara.",
            )
        )
    for control in main.select(
        ".icone-ajuda, .veja-mais, .exibir-todo-conteudo, .modal, "
        ".link-noticias, .g-agenda-link-todas, .atuacao__links-adicionais, "
        ".presencas__section[aria-hidden=true], script, style"
    ):
        control.decompose()
    for anchor in main.select(".identificacao-deputado a"):
        if text(anchor) in {"Biografia completa", "Siga por e-mail", "Fale com o deputado"}:
            anchor.decompose()
        else:
            anchor.unwrap()
    sections: list[ReportSection] = []
    for selector, section_title in (
        (".identificacao-deputado", "Identificação e contato"),
        (".atividades-deputado", "Períodos disponíveis"),
        (".atuacao-deputado", "Atuação, presença e comissões"),
        (".cargos-deputado", "Cargos"),
        (".emendas-deputado", "Emendas ao orçamento"),
        (".gastos-deputado", "Gastos públicos"),
        (".recursos-deputado", "Recursos e benefícios"),
        (".agenda-deputado", "Agenda"),
        (".noticias-deputado", "Notícias publicadas pela Câmara"),
    ):
        node = main.select_one(selector)
        if node:
            sections.append(ReportSection(title=section_title, blocks=blocks(node)))
    return Dashboard(
        politician=politician,
        year=text(year_node) if year_node else None,
        fetched_at=datetime.now(UTC),
        updates=updates,
        metrics=metrics,
        sections=sections,
    )
