from pydantic import BaseModel

from app.biography import folded

SOURCE_URL = (
    "https://dspace.sti.ufcg.edu.br/bitstream/riufcg/30300/1/"
    "O%20PODER%20DAS%20FAM%C3%8DLIAS%20E%20AS%20FAM%C3%8DLIAS%20DO%20PODER%20-%20"
    "CAP%20DE%20LIVRO%20CDSA%202018.pdf"
)


class CuratedPerson(BaseModel):
    id: str
    name: str
    public_roles: str


class FamilyLink(BaseModel):
    source_id: str
    target_id: str
    relationship: str
    evidence: str
    evidence_url: str = SOURCE_URL


class CuratedFamily(BaseModel):
    slug: str
    name: str
    period: str
    summary: str
    people: list[CuratedPerson]
    links: list[FamilyLink]
    source_title: str
    source_url: str = SOURCE_URL
    notice: str = (
        "Recorte inicial baseado nas relações explicitamente documentadas na fonte. "
        "Não representa todos os integrantes nem prova influência indevida."
    )


FAMILIES = [
    CuratedFamily(
        slug="cunha-lima",
        name="Família Cunha Lima",
        period="1870–2015 na fonte",
        summary=(
            "Núcleo político paraibano apresentado no capítulo com vínculos entre quatro "
            "gerações e atuação municipal, estadual e federal."
        ),
        people=[
            CuratedPerson(
                id="ivandro",
                name="Ivandro Cunha Lima",
                public_roles="Ex-senador e ex-prefeito de Campina Grande",
            ),
            CuratedPerson(
                id="ronaldo",
                name="Ronaldo Cunha Lima",
                public_roles="Ex-governador, ex-senador e ex-prefeito",
            ),
            CuratedPerson(
                id="cassio", name="Cássio Cunha Lima", public_roles="Ex-governador e ex-senador"
            ),
            CuratedPerson(id="pedro", name="Pedro Cunha Lima", public_roles="Ex-deputado federal"),
            CuratedPerson(
                id="romero", name="Romero Rodrigues", public_roles="Deputado federal e ex-prefeito"
            ),
            CuratedPerson(
                id="fernando",
                name="Fernando Rodrigues Catão",
                public_roles="Atuação pública documentada na fonte",
            ),
        ],
        links=[
            FamilyLink(
                source_id="ivandro",
                target_id="ronaldo",
                relationship="irmãos",
                evidence="O capítulo identifica Ivandro como irmão de Ronaldo Cunha Lima (p. 233).",
            ),
            FamilyLink(
                source_id="ronaldo",
                target_id="cassio",
                relationship="pai e filho",
                evidence="Ronaldo é apresentado como pai de Cássio Cunha Lima (p. 234).",
            ),
            FamilyLink(
                source_id="cassio",
                target_id="pedro",
                relationship="pai e filho",
                evidence="Pedro é apresentado como filho de Cássio e neto de Ronaldo (p. 235–236).",
            ),
            FamilyLink(
                source_id="cassio",
                target_id="romero",
                relationship="primos",
                evidence="Romero Rodrigues é identificado como primo de Cássio (p. 233).",
            ),
            FamilyLink(
                source_id="fernando",
                target_id="cassio",
                relationship="tio materno e sobrinho",
                evidence=(
                    "Fernando Rodrigues Catão é identificado como tio materno de Cássio (p. 234)."
                ),
            ),
        ],
        source_title="O poder das famílias e as famílias do poder — capítulo acadêmico (UFCG)",
    ),
    CuratedFamily(
        slug="maia",
        name="Família Maia",
        period="1930–2018 na fonte",
        summary=(
            "Relações políticas documentadas entre integrantes com atuação no Rio Grande do "
            "Norte, no Rio de Janeiro e em instituições federais."
        ),
        people=[
            CuratedPerson(
                id="cesar", name="César Maia", public_roles="Ex-prefeito do Rio de Janeiro"
            ),
            CuratedPerson(
                id="rodrigo",
                name="Rodrigo Maia",
                public_roles="Ex-presidente da Câmara dos Deputados",
            ),
            CuratedPerson(
                id="agripino", name="José Agripino Maia", public_roles="Ex-governador e ex-senador"
            ),
            CuratedPerson(id="felipe", name="Felipe Maia", public_roles="Ex-deputado federal"),
            CuratedPerson(id="zenaide", name="Zenaide Maia", public_roles="Senadora"),
            CuratedPerson(id="joao", name="João Maia", public_roles="Deputado federal"),
        ],
        links=[
            FamilyLink(
                source_id="cesar",
                target_id="rodrigo",
                relationship="pai e filho",
                evidence="Rodrigo Maia é apresentado como filho de César Maia (p. 237).",
            ),
            FamilyLink(
                source_id="agripino",
                target_id="felipe",
                relationship="pai e filho",
                evidence="Felipe Maia é apresentado como filho de José Agripino Maia (p. 238–239).",
            ),
            FamilyLink(
                source_id="zenaide",
                target_id="joao",
                relationship="irmãos",
                evidence="Zenaide Maia é apresentada como irmã de João Maia (p. 239).",
            ),
            FamilyLink(
                source_id="rodrigo",
                target_id="agripino",
                relationship="primos",
                evidence=(
                    "O capítulo descreve Rodrigo Maia e José Agripino Maia como primos (p. 237)."
                ),
            ),
        ],
        source_title="O poder das famílias e as famílias do poder — capítulo acadêmico (UFCG)",
    ),
]


def curated_families() -> list[CuratedFamily]:
    return FAMILIES


def curated_family_for(name: str) -> tuple[CuratedFamily, CuratedPerson] | None:
    wanted = folded(name)
    for family in FAMILIES:
        for person in family.people:
            if folded(person.name) == wanted:
                return family, person
    return None
