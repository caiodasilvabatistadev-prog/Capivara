from typing import Any, Protocol

import httpx

from app.models import Politician


class Provider(Protocol):
    async def search(self, name: str) -> list[Politician]: ...
    async def get(self, official_id: int) -> Politician: ...


class CamaraProvider:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    @staticmethod
    def normalize(data: dict[str, Any]) -> Politician:
        current = data.get("ultimoStatus", data)
        official_id = int(data["id"])
        return Politician(
            id=official_id,
            name=current["nome"],
            party=current["siglaPartido"],
            state=current["siglaUf"],
            email=current.get("email"),
            photo_url=current.get("urlFoto"),
            source_url=f"https://www.camara.leg.br/deputados/{official_id}",
        )

    async def search(self, name: str) -> list[Politician]:
        results: list[Politician] = []
        page = 1
        while True:
            response = await self.client.get(
                "deputados", params={"nome": name, "itens": 100, "pagina": page}
            )
            response.raise_for_status()
            payload = response.json()
            results.extend(self.normalize(item) for item in payload["dados"])
            if not any(link["rel"] == "next" for link in payload.get("links", [])):
                return results
            page += 1

    async def get(self, official_id: int) -> Politician:
        response = await self.client.get(f"deputados/{official_id}")
        response.raise_for_status()
        return self.normalize(response.json()["dados"])
