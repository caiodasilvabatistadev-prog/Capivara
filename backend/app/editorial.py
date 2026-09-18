from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, HttpUrl, model_validator

from app.directories import folded
from app.models import Politician

Status = Literal[
    "condenacao_definitiva",
    "condenacao_recorrivel",
    "em_andamento",
    "absolvido",
    "arquivado",
    "anulado",
    "pedido_rejeitado",
]


class Source(BaseModel):
    publisher: str
    url: HttpUrl
    published_at: date


class JudicialCase(BaseModel):
    title: str
    summary: str
    category: Literal["corrupcao", "eleitoral", "criminal", "civel", "administrativo"]
    status: Status
    court: str
    case_number: str
    status_as_of: date
    final_judgment: bool
    official_source: Source
    journalism: Source

    @model_validator(mode="after")
    def check_evidence(self) -> Self:
        host = self.official_source.url.host or ""
        if not host.endswith(".jus.br"):
            raise ValueError("O estado judicial exige fonte oficial de tribunal")
        if self.status == "condenacao_definitiva" and not self.final_judgment:
            raise ValueError("Condenação definitiva exige trânsito em julgado verificado")
        if self.status in {"em_andamento", "condenacao_recorrivel"} and self.final_judgment:
            raise ValueError("Processo em curso não pode ter trânsito em julgado informado")
        return self


class PublicAction(BaseModel):
    title: str
    summary: str
    attribution: str
    stage: Literal["proposta", "aprovada", "executada"]
    stage_as_of: date
    official_source: Source
    journalism: Source


class PublicContext(BaseModel):
    subject_name: str
    reviewed_at: date | None = None
    actions: list[PublicAction] = []
    cases: list[JudicialCase] = []
    notice: str = (
        "Curadoria inicial, sem levantamento completo de notícias ou processos. "
        "Os estados se referem à data indicada em cada registro; "
        "mudanças posteriores podem existir. "
        "Ausência de registro não atesta ausência de processos. Não há nota ou ranking político."
    )


CATALOG: dict[tuple[str, int], PublicContext] = {
    ("senado", 6331): PublicContext(
        subject_name="Sergio Moro",
        reviewed_at=date(2026, 9, 18),
        cases=[
            JudicialCase(
                title="Ações eleitorais sobre despesas de pré-campanha",
                summary="O TSE manteve a improcedência dos pedidos de cassação. "
                "Este registro é eleitoral e não constitui condenação por corrupção.",
                category="eleitoral",
                status="pedido_rejeitado",
                court="TSE",
                case_number="RO 0604176-51.2022.6.16.0000 e RO 0604298-64.2022.6.16.0000",
                status_as_of=date(2024, 5, 21),
                final_judgment=False,
                official_source=Source(
                    publisher="Tribunal Superior Eleitoral",
                    published_at=date(2024, 5, 21),
                    url=HttpUrl(
                        "https://www.tse.jus.br/comunicacao/noticias/2024/Maio/tse-mantem-improcedencia-de-acoes-que-pediam-a-cassacao-do-senador-sergio-moro"
                    ),
                ),
                journalism=Source(
                    publisher="Exame",
                    published_at=date(2024, 5, 21),
                    url=HttpUrl(
                        "https://exame.com/brasil/tse-formar-maioria-e-sergio-moro-mantem-seu-mandato/"
                    ),
                ),
            )
        ],
        actions=[
            PublicAction(
                title="Lei 15.245/2025: proteção a agentes contra o crime organizado",
                summary="A norma prevê proteção a agentes públicos e familiares "
                "e trata da obstrução "
                "de investigações. A sanção não comprova execução nem impacto medido.",
                attribution="Projeto de autoria de Sergio Moro, aprovado pelo Congresso "
                "e sancionado "
                "pelo presidente da República. Não é uma realização individual exclusiva.",
                stage="aprovada",
                stage_as_of=date(2025, 10, 30),
                official_source=Source(
                    publisher="Agência Senado",
                    published_at=date(2025, 11, 19),
                    url=HttpUrl(
                        "https://webstories.senado.leg.br/web-stories/protecao-a-agentes-publicos-contra-o-crime-organizado/"
                    ),
                ),
                journalism=Source(
                    publisher="A TARDE",
                    published_at=date(2025, 10, 30),
                    url=HttpUrl(
                        "https://atarde.com.br/politica/antagonistas-lula-sanciona-lei-de-moro-que-endurece-combate-ao-crime-1366550"
                    ),
                ),
            )
        ],
    ),
}


def context_for(person: Politician) -> PublicContext:
    entry = CATALOG.get((person.provider, person.id))
    if entry is not None and folded(entry.subject_name) == folded(person.name):
        return entry
    return PublicContext(subject_name=person.name)
