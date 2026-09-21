from datetime import UTC, datetime
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from app.biography import HEADERS, WIKIPEDIA, folded
from app.family_registry import curated_family_for
from app.models import Politician

WIKIDATA = "https://www.wikidata.org"
KINSHIP = {"P22": "pai", "P25": "mãe", "P26": "cônjuge", "P40": "filho(a)", "P3373": "irmão/irmã"}


class FamilyMember(BaseModel):
    name: str
    relationship: str
    description: str = ""
    evidence_url: str
    political_profile: bool = False


class PoliticalFamily(BaseModel):
    found: bool
    members: list[FamilyMember] = []
    source_url: str = ""
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notice: str = (
        "Só exibimos parentescos acompanhados de referência na base consultada. "
        "A ausência de resultado não prova que não exista parentesco político."
    )


def has_political_profile(description: str) -> bool:
    value = folded(description)
    return any(
        term in value
        for term in (
            "politic",
            "deputad",
            "senador",
            "vereador",
            "prefeit",
            "governador",
            "presidente",
            "ministr",
        )
    )


async def documented_family(client: httpx.AsyncClient, person: Politician) -> PoliticalFamily:
    curated = curated_family_for(person.name)
    if curated:
        family, subject = curated
        people = {item.id: item for item in family.people}
        members = []
        for link in family.links:
            if subject.id not in (link.source_id, link.target_id):
                continue
            curated_related_id = link.target_id if link.source_id == subject.id else link.source_id
            related = people[curated_related_id]
            description = f"{related.public_roles}. {link.evidence}"
            members.append(
                FamilyMember(
                    name=related.name,
                    relationship=link.relationship,
                    description=description,
                    evidence_url=link.evidence_url,
                    political_profile=has_political_profile(description),
                )
            )
        return PoliticalFamily(found=bool(members), members=members, source_url=family.source_url)
    search = await client.get(
        WIKIPEDIA + "/w/rest.php/v1/search/page",
        params={"q": person.name, "limit": 5},
        headers=HEADERS,
    )
    search.raise_for_status()
    candidate = next(
        (
            page
            for page in search.json().get("pages", [])
            if folded(str(page.get("title", ""))) == folded(person.name)
        ),
        None,
    )
    if candidate is None:
        return PoliticalFamily(found=False)
    title = str(candidate["title"])
    summary = await client.get(
        WIKIPEDIA + "/api/rest_v1/page/summary/" + quote(title, safe=""), headers=HEADERS
    )
    summary.raise_for_status()
    qid = str(summary.json().get("wikibase_item") or "")
    if not qid:
        return PoliticalFamily(found=False)
    entity_response = await client.get(
        f"{WIKIDATA}/wiki/Special:EntityData/{qid}.json", headers=HEADERS
    )
    entity_response.raise_for_status()
    entity = entity_response.json()["entities"][qid]
    claims = entity.get("claims", {})
    selected: list[tuple[str, str]] = []
    for prop, relationship in KINSHIP.items():
        for claim in claims.get(prop, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            related_id = value.get("id") if isinstance(value, dict) else None
            if related_id and claim.get("references"):
                selected.append((related_id, relationship))
    if not selected:
        return PoliticalFamily(found=False, source_url=f"{WIKIDATA}/wiki/{qid}")
    ids = list(dict.fromkeys(item[0] for item in selected))
    labels_response = await client.get(
        WIKIDATA + "/w/api.php",
        params={
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": "labels|descriptions",
            "languages": "pt|en",
            "format": "json",
        },
        headers=HEADERS,
    )
    labels_response.raise_for_status()
    entities = labels_response.json()["entities"]
    members = []
    for related_id, relationship in selected:
        related = entities[related_id]
        labels = related.get("labels", {})
        descriptions = related.get("descriptions", {})
        name = (labels.get("pt") or labels.get("en") or {}).get("value", related_id)
        description = (descriptions.get("pt") or descriptions.get("en") or {}).get("value", "")
        members.append(
            FamilyMember(
                name=name,
                relationship=relationship,
                description=description,
                evidence_url=f"{WIKIDATA}/wiki/{qid}#{relationship}",
                political_profile=has_political_profile(description),
            )
        )
    return PoliticalFamily(found=True, members=members, source_url=f"{WIKIDATA}/wiki/{qid}")
