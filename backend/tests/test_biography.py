import httpx
import respx
from fastapi.testclient import TestClient

from app.biography import WIKIPEDIA, folded, media_context, parse_media, wikipedia_biography
from app.main import app
from app.models import Politician
from app.news import FEED

PERSON = Politician(
    id=1,
    name="José Árvore",
    party="ABC",
    state="SP",
    source_url="https://www.camara.leg.br/deputados/1",
)


@respx.mock
async def test_wikipedia_exact_name_and_safe_fallbacks():
    respx.get(FEED).respond(200, content=b"<rss><channel/></rss>")
    respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "Outro"}, {"title": "José Árvore"}]}
    )
    respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Jos%C3%A9%20%C3%81rvore").respond(
        200,
        json={
            "title": "José Árvore",
            "description": "político brasileiro",
            "extract": "José é um político brasileiro.",
            "content_urls": {"desktop": {"page": "https://pt.wikipedia.org/wiki/José_Árvore"}},
        },
    )
    async with httpx.AsyncClient() as client:
        data = await wikipedia_biography(client, PERSON)
    assert data.found and data.extract.startswith("José")
    assert data.source_url.endswith("José_Árvore")
    assert folded("  JOSÉ Árvore  ") == "jose arvore"
    respx.get(FEED).respond(503)
    async with httpx.AsyncClient() as client:
        assert (await wikipedia_biography(client, PERSON)).media == []


@respx.mock
async def test_wikipedia_rejects_homonym_and_empty_article():
    respx.get(FEED).respond(200, content=b"<rss><channel/></rss>")
    search = respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(
        200, json={"pages": [{"title": "José Árvore (cantor)"}]}
    )
    async with httpx.AsyncClient() as client:
        assert not (await wikipedia_biography(client, PERSON)).found
        search.respond(200, json={"pages": [{"title": "José Árvore"}]})
        respx.get(WIKIPEDIA + "/api/rest_v1/page/summary/Jos%C3%A9%20%C3%81rvore").respond(
            200, json={"extract": "", "content_urls": None}
        )
        assert not (await wikipedia_biography(client, PERSON)).found


@respx.mock
def test_biography_route_and_invalid_identity():
    respx.get(FEED).respond(200, content=b"<rss><channel/></rss>")
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").respond(
        200,
        json={
            "dados": {
                "id": 1,
                "ultimoStatus": {"nome": "Maria", "siglaPartido": "X", "siglaUf": "SP"},
            }
        },
    )
    respx.get(WIKIPEDIA + "/w/rest.php/v1/search/page").respond(200, json={"pages": []})
    with TestClient(app) as client:
        assert client.get("/politicians/camara/1/biography").json()["found"] is False
        assert client.get("/politicians/camara/0/biography").status_code == 422


@respx.mock
async def test_media_context_filters_and_orders():
    feed = (
        b"<rss><channel><item><title>Jose Arvore apresenta projeto</title>"
        b"<source url='https://g1.globo.com'>G1</source>"
        b"<link>https://news.google.com/a</link>"
        b"<pubDate>Fri, 19 Sep 2026 12:00:00 GMT</pubDate></item>"
        b"<item><title>Outro nome</title><source url='https://g1.globo.com'>G1</source>"
        b"<link>https://news.google.com/b</link>"
        b"<pubDate>Fri, 19 Sep 2026 13:00:00 GMT</pubDate></item>"
        b"<item><title>Jose Arvore sem data</title>"
        b"<source url='https://uol.com.br'>UOL</source>"
        b"<link>https://news.google.com/c</link><pubDate>invalida</pubDate></item>"
        b"</channel></rss>"
    )
    respx.get(FEED).respond(200, content=feed)
    async with httpx.AsyncClient() as client:
        items = await media_context(client, PERSON.name)
    assert len(items) == 1 and items[0].publisher == "G1"


def test_media_rejects_invalid_feeds():
    for content in (b"<!DOCTYPE html>", b"<invalid", b"<html/>"):
        try:
            parse_media(content, PERSON.name)
        except ValueError:
            pass
        else:
            raise AssertionError("feed inválido aceito")
