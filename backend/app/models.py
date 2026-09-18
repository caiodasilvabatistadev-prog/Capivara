from pydantic import BaseModel


class Politician(BaseModel):
    id: int
    provider: str = "camara"
    role: str = "Deputado federal"
    institution: str = "Câmara dos Deputados"
    power: str = "legislativo"
    name: str
    party: str
    state: str
    email: str | None = None
    photo_url: str | None = None
    source_url: str
