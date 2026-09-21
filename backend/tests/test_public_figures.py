from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.public_figures import PRESIDENTS, CatalogProvider, Figure, HistoricalCamaraProvider


@pytest.mark.asyncio
async def test_catalog_search_dashboard_and_missing():
    provider = CatalogProvider(
        AsyncMock(),
        "stf",
        [Figure(1, "Álvaro Silva", "Ministro", "Tribunal", "https://example.org")],
    )
    assert (await provider.search("alvaro"))[0].power == "judiciario"
    assert (await provider.get(1)).name == "Álvaro Silva"
    assert (await provider.dashboard(1)).politician.provider == "stf"
    with pytest.raises(HTTPException):
        await provider.get(2)


@pytest.mark.asyncio
async def test_presidential_dashboard_has_current_president_and_documented_actions():
    provider = CatalogProvider(AsyncMock(), "presidentes", PRESIDENTS)
    current = await provider.dashboard(100)
    assert current.politician.name == "Luiz Inácio Lula da Silva"
    section = next(item for item in current.sections if item.title.startswith("Obras"))
    assert section.blocks[0].rows[0][-1] == "Fonte oficial"


@pytest.mark.asyncio
async def test_historical_camara_search_get_and_dashboard():
    client = AsyncMock()
    responses = []
    for _ in range(9):
        response = Mock()
        response.json.return_value = {
            "dados": [{"id": 7, "nome": "Pessoa Histórica", "siglaPartido": "ABC", "siglaUf": "SP"}]
        }
        responses.append(response)
    detail = Mock()
    detail.json.return_value = {
        "dados": {
            "id": 7,
            "ultimoStatus": {"nome": "Pessoa Histórica", "siglaPartido": "ABC", "siglaUf": "SP"},
        }
    }
    client.get.side_effect = responses + [detail, detail]
    provider = HistoricalCamaraProvider(client)
    found = await provider.search("Pessoa")
    assert len(found) == 1 and found[0].provider == "camara_historica"
    assert (await provider.get(7)).role.startswith("Ex-deputado")
    dashboard = await provider.dashboard(7)
    assert dashboard.politician.provider == "camara_historica"
