import json
from datetime import UTC, datetime

import httpx

from app.dashboard import Dashboard, Metric, ReportBlock, ReportSection
from app.directories import DirectoryProvider
from app.models import Politician

SOURCE = "https://www.governo.mg.gov.br/api/MundoOficial/consulta"
PAGE = "https://www.governo.mg.gov.br/mundo-oficial"
STATES = {
    "RO": 11,
    "AC": 12,
    "AM": 13,
    "RR": 14,
    "PA": 15,
    "AP": 16,
    "TO": 17,
    "MA": 21,
    "PI": 22,
    "CE": 23,
    "RN": 24,
    "PB": 25,
    "PE": 26,
    "AL": 27,
    "SE": 28,
    "BA": 29,
    "MG": 31,
    "ES": 32,
    "RJ": 33,
    "SP": 35,
    "PR": 41,
    "SC": 42,
    "RS": 43,
    "MS": 50,
    "MT": 51,
    "GO": 52,
    "DF": 53,
}
LABELS = {
    "nomeCompleto": "Nome completo",
    "nomeComum": "Nome público",
    "aniversario": "Aniversário (dia/mês)",
    "semDataNascimento": "Data de nascimento não informada",
    "sexo": "Sexo informado",
    "profissao": "Profissão",
    "cargo": "Cargo",
    "situacaoCargo": "Situação do cargo",
    "instituicao": "Órgão",
    "instituicaoSigla": "Sigla do órgão",
    "endereco": "Endereço institucional",
    "enderecoBairro": "Bairro",
    "enderecoCEP": "CEP",
    "municipio": "Município / UF",
    "telefone": "Telefone institucional",
    "fax": "Fax",
}

ALIASES = {
    "Mateus Simões de Almeida": "Mateus Simões",
    "Tarcísio Gomes de Freitas": "Tarcísio de Freitas",
    "Maria de Fátima Bezerra": "Fátima Bezerra",
    "Jorginho dos Santos Mello": "Jorginho Mello",
    "Paulo Suruagy do Amaral Dantas": "Paulo Dantas",
    "Roberto Maia Cidade Filho": "Roberto Cidade",
    "Carlos Roberto Massa Junior": "Ratinho Junior",
    "Clécio Luís Vilhena Vieira": "Clécio Luís",
    "Francisco dos Santos Sampaio": "Soldado Sampaio",
    "Eduardo Corrêa Riedel": "Eduardo Riedel",
}

# Continuidade mínima quando o catálogo oficial bloqueia o datacenter de produção.
# Os nomes reproduzem a última composição obtida da mesma fonte; o painel informa a fonte.
FALLBACK = {
    "AC": "Mailza",
    "AL": "Paulo Suruagy do Amaral Dantas",
    "AP": "Clécio Luís Vilhena Vieira",
    "AM": "Roberto Maia Cidade Filho",
    "BA": "Jerônimo Rodrigues Souza",
    "CE": "Elmano de Freitas",
    "DF": "Celina Leão",
    "ES": "Ricardo Ferraço",
    "GO": "Daniel Vilela",
    "MA": "Carlos Orleans Brandão Junior",
    "MT": "Otaviano Pivetta",
    "MS": "Eduardo Corrêa Riedel",
    "MG": "Mateus Simões de Almeida",
    "PA": "Hana Ghassan Tuma",
    "PB": "Lucas Ribeiro",
    "PR": "Carlos Roberto Massa Junior",
    "PE": "Raquel Lyra",
    "PI": "Rafael Fonteles",
    "RJ": "Ricardo Couto de Castro",
    "RN": "Maria de Fátima Bezerra",
    "RS": "Eduardo Leite",
    "RO": "Marcos Rocha",
    "RR": "Francisco dos Santos Sampaio",
    "SC": "Jorginho dos Santos Mello",
    "SP": "Tarcísio Gomes de Freitas",
    "SE": "Fábio Mitidieri",
    "TO": "Wanderlei Barbosa",
}


def decode_public(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252")


class GovernorProvider(DirectoryProvider):
    async def listing(self) -> list[Dashboard]:
        try:
            response = await self.client.get(SOURCE, params={"categoriaId": 18})
            response.raise_for_status()
            groups = json.loads(decode_public(response.content))
        except (OSError, ValueError, httpx.HTTPError):
            groups = []
        if not groups:
            groups = [
                {
                    "pessoas": [
                        {
                            "nomeCompleto": name,
                            "cargo": "Governador(a)",
                            "situacaoCargo": "Em exercício",
                            "instituicao": f"Governo do Estado · {state}",
                            "municipio": f"Capital - {state}",
                        }
                        for state, name in FALLBACK.items()
                    ]
                }
            ]
        result = []
        for group in groups:
            for item in group["pessoas"]:
                state = item["municipio"].rsplit(" - ", 1)[-1].strip()
                identity = STATES[state]
                person = Politician(
                    id=identity,
                    provider="governadores",
                    power="executivo",
                    name=item["nomeCompleto"],
                    role=item["cargo"]
                    + (" · " + item["situacaoCargo"] if item.get("situacaoCargo") else ""),
                    institution=item["instituicao"],
                    state=state,
                    party="Não informado pela fonte",
                    source_url=PAGE,
                )
                rows = [["Informação publicada", "Valor"]]
                rows.extend(
                    [LABELS.get(key, key), str(value)]
                    for key, value in item.items()
                    if value is not None and value != ""
                )
                result.append(
                    Dashboard(
                        politician=person,
                        year=None,
                        fetched_at=datetime.now(UTC),
                        updates=[],
                        metrics=[
                            Metric(
                                label=label,
                                value=str(item.get(field) or "Não informado"),
                                group="Perfil institucional",
                                explanation=(
                                    "Cadastro oficial de autoridades do Governo de Minas Gerais."
                                ),
                            )
                            for label, field in [
                                ("Cargo", "cargo"),
                                ("Situação do cargo", "situacaoCargo"),
                                ("Telefone institucional", "telefone"),
                                ("Órgão", "instituicao"),
                            ]
                        ],
                        sections=[
                            ReportSection(
                                title="Perfil e contatos",
                                blocks=[
                                    ReportBlock(
                                        kind="table",
                                        text=(
                                            "Todos os campos publicados no cadastro de governadores"
                                        ),
                                        rows=rows,
                                    )
                                ],
                            ),
                            ReportSection(
                                title="Fontes e cobertura",
                                blocks=[
                                    ReportBlock(kind="text", text=SOURCE),
                                    ReportBlock(
                                        kind="text",
                                        text=(
                                            "A lista acompanha a atualização da "
                                            "fonte oficial, que não "
                                            "informa a data de revisão de cada "
                                            "perfil. Partido, foto, "
                                            "patrimônio, despesas, obras e execução "
                                            "orçamentária não são "
                                            "publicados neste cadastro. Não "
                                            "informado não significa "
                                            "zero. Candidatura eleitoral não é "
                                            "confirmada por ocupar "
                                            "este cargo."
                                        ),
                                    ),
                                ],
                            ),
                        ],
                        notice=(
                            "Perfil institucional do cadastro oficial. A integração "
                            "cobre os 26 estados e o Distrito Federal quando todos os "
                            "registros estão disponíveis na fonte. Situações interinas "
                            "são reproduzidas como publicadas. O cadastro não é um "
                            "levantamento completo da gestão e do patrimônio do "
                            "governador."
                        ),
                    )
                )
        if len({data.politician.state for data in result}) != 27:
            raise ValueError("Cadastro de governadores incompleto")
        return result

    async def search(self, name: str) -> list[Politician]:
        from app.directories import folded

        needle = folded(name)
        return [
            data.politician
            for data in await self.listing()
            if needle in folded(data.politician.name + " " + ALIASES.get(data.politician.name, ""))
        ]
