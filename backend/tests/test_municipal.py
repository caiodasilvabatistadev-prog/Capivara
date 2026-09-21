from unittest.mock import AsyncMock, patch

import httpx

from app.elections import ElectionProvider, MunicipalElectedProvider


async def test_municipal_provider_keeps_only_elected_mayors_and_councillors():
    rows = [
        {
            "SQ_CANDIDATO": "1",
            "NM_URNA_CANDIDATO": "Maria",
            "DS_CARGO": "PREFEITO",
            "DS_SIT_TOT_TURNO": "ELEITO",
            "NM_UE": "Cidade Nova",
            "SG_UF": "SP",
            "SG_PARTIDO": "ABC",
        },
        {"DS_CARGO": "VEREADOR", "DS_SIT_TOT_TURNO": "NÃO ELEITO"},
        {"DS_CARGO": "DEPUTADO FEDERAL", "DS_SIT_TOT_TURNO": "ELEITO"},
    ]
    async with httpx.AsyncClient() as client:
        source = MunicipalElectedProvider(client, 2024)
        with patch.object(ElectionProvider, "records", AsyncMock(return_value=rows)):
            assert await source.records("Maria") == [rows[0]]
        person = source.person(rows[0])
    assert person.provider == "municipais"
    assert person.role == "Prefeito eleito(a) · mandato municipal"
    assert person.institution == "Cidade Nova · SP"
