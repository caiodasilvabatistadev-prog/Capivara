import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.parties import PARTIES, PartyProvider
from app.rankings import party_snapshot


@pytest.mark.asyncio
async def test_presidents_and_profiles():
    source = PartyProvider()
    for party in PARTIES.values():
        person = await source.get(party.id)
        assert person.name == party.president
        assert person.role == "Presidente nacional de partido"
        report = await source.dashboard(party.id)
        assert not report.metrics
        assert "não ao presidente pessoalmente" in report.notice
    assert [p.name for p in await source.search("edinho")] == ["Edinho Silva"]
    assert await source.search("inexistente") == []
    with pytest.raises(HTTPException) as error:
        await source.get(999)
    assert error.value.status_code == 404
    for metric, year in [("party_fund", 2025), ("election_fund", 2026)]:
        result = party_snapshot(metric, year)
        assert all(entry.party and entry.party.sigla == entry.name for entry in result.entries)
    with TestClient(app) as client:
        assert (
            client.get("/politicians/partidos/22/dashboard").json()["politician"]["name"]
            == "Valdemar Costa Neto"
        )
        assert client.get("/politicians/partidos/999").status_code == 404
