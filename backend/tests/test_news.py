from xml.sax.saxutils import escape

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.news import FEED, parse_news, search_news


def item(
    title="Sergio Moro investigado - G1",
    source="https://g1.globo.com",
    link="https://news.google.com/rss/articles/abc",
    date="Tue, 21 May 2024 12:00:00 GMT",
):
    return (
        f'<item><title>{escape(title)}</title><source url="{source}">G1</source>'
        f"<link>{link}</link><pubDate>{date}</pubDate></item>"
    )


def feed(items):
    return ("<rss><channel>" + items + "</channel></rss>").encode()


def test_filtering_sources_names_dates_and_deduplication():
    variants = [
        item(),
        item(),
        item(
            "Sergio Moro condenado - Folha",
            "https://www1.folha.uol.com.br",
            date="Wed, 22 May 2024 12:00:00 GMT",
        ),
        item("Sergio Moro: crime, apologia, suspeito, julgado"),
        item("Sergio Moro fala sobre educação"),
        item("Outra Pessoa investigada"),
        item(source="https://g1.globo.com.evil.test"),
        item(source="http://g1.globo.com"),
        item(link="https://evil.test/a"),
        item(link="http://news.google.com/a"),
        item("Sergio Moro investigado inválido", date="invalid"),
        item("Sergio Moro investigado sem fuso", date="Tue, 21 May 2024 12:00:00"),
        "<item><title>Sergio Moro investigado</title></item>",
    ]
    result = parse_news(feed("".join(variants)), "Sérgio Moro")
    assert len(result) == 3
    assert result[0].publisher == "Folha de S.Paulo"
    assert result[0].matched_terms == ["condenação"]
    assert result[-1].matched_terms == ["suspeita", "julgamento", "apologia", "crime"]
    assert (
        len(
            parse_news(
                feed(
                    "".join(
                        item(f"Sergio Moro investigado {n}", link=f"https://news.google.com/{n}")
                        for n in range(25)
                    )
                ),
                "Sergio Moro",
            )
        )
        == 20
    )


@pytest.mark.parametrize(
    "content",
    [b"x", b"<html/>", b"<!DOCTYPE rss><rss/>", b"x" * 2_000_001],
    ids=["invalid-xml", "wrong-root", "doctype", "oversized"],
)
def test_invalid_feeds(content):
    with pytest.raises(ValueError):
        parse_news(content, "Sergio Moro")


@respx.mock
async def test_fetch_empty_and_errors():
    route = respx.get(FEED).mock(return_value=httpx.Response(200, content=feed("")))
    async with httpx.AsyncClient() as client:
        result = await search_news(client, 'Sergio "Moro"')
        assert result.items == []
        query = route.calls[0].request.url.params["q"]
        assert '"Sergio Moro"' in query and "site:g1.globo.com" in query
        route.mock(return_value=httpx.Response(503))
        with pytest.raises(httpx.HTTPStatusError):
            await search_news(client, "Sergio Moro")


@respx.mock
def test_news_endpoint_uses_official_identity():
    respx.get("https://dadosabertos.camara.leg.br/api/v2/deputados/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "dados": {
                    "id": 1,
                    "ultimoStatus": {
                        "nome": "Sergio Moro",
                        "siglaPartido": "X",
                        "siglaUf": "PR",
                        "urlFoto": "https://example.com/a.jpg",
                    },
                }
            },
        )
    )
    respx.get(FEED).mock(return_value=httpx.Response(200, content=feed(item())))
    with TestClient(app) as client:
        assert client.get("/politicians/camara/1/news").json()["items"][0]["publisher"] == "G1"
        assert client.get("/politicians/camara/0/news").status_code == 422
        assert client.get("/politicians/unknown/1/news").status_code == 404
