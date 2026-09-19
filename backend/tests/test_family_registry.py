from app.family_registry import curated_families, curated_family_for


def test_curated_families_have_documented_links():
    families = curated_families()
    assert [family.slug for family in families] == ["cunha-lima", "maia"]
    assert all(family.people and family.links for family in families)
    assert all(
        link.evidence_url.startswith("https://dspace.sti.ufcg.edu.br/")
        for family in families
        for link in family.links
    )


def test_curated_family_lookup():
    found = curated_family_for("CASSIO CUNHA LIMA")
    assert found and found[0].slug == "cunha-lima" and found[1].id == "cassio"
    assert curated_family_for("Pessoa inexistente") is None
