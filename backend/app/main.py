from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.concurrency import run_in_threadpool

from app.dashboard import Dashboard
from app.directories import ExecutiveProvider, JudicialProvider, SenateProvider
from app.editorial import PublicContext, context_for
from app.models import Politician
from app.pdf_report import make_pdf
from app.providers import CamaraProvider, Provider
from app.rankings import MetricName, Ranking, ranking


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")
    cors_origins: list[str] = ["http://localhost:3000"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient(
        base_url="https://dadosabertos.camara.leg.br/api/v2/",
        timeout=15,
        headers={"Accept": "application/json"},
    ) as client:
        app.state.http_client = client
        app.state.providers = {
            "camara": CamaraProvider(client),
            "senado": SenateProvider(client),
            "executivo": ExecutiveProvider(client),
            "judiciario": JudicialProvider(client),
        }
        yield


app = FastAPI(title="Consulta Pública", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(httpx.HTTPError)
async def upstream_error(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    missing = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404
    return JSONResponse(
        status_code=404 if missing else 502,
        content={"detail": "Parlamentar não encontrado" if missing else "Fonte indisponível"},
    )


@app.exception_handler(ValueError)
@app.exception_handler(KeyError)
@app.exception_handler(TypeError)
@app.exception_handler(ValidationError)
async def invalid_upstream(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": "Resposta inválida da fonte"})


def provider_for(request: Request, name: str) -> Provider:
    providers: dict[str, Provider] = request.app.state.providers
    if name not in providers:
        raise HTTPException(404, "Provider não encontrado")
    return providers[name]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
async def search(
    request: Request,
    q: str = Query(min_length=2, max_length=100),
    provider: str = Query(default="camara", pattern="^(camara|senado|executivo|judiciario)$"),
) -> list[Politician]:
    name = q.strip()
    if len(name) < 2:
        raise HTTPException(422, "Informe pelo menos dois caracteres")
    return await provider_for(request, provider).search(name)


@app.get("/rankings")
async def public_rankings(
    request: Request,
    provider: str = Query(default="camara", pattern="^(camara|senado|executivo|judiciario)$"),
    metric: MetricName = "expenses",
    year: int = Query(default=datetime.now(UTC).year, ge=2024, le=datetime.now(UTC).year),
) -> Ranking:
    source = provider_for(request, provider)
    return await ranking(request.app.state.http_client, source, provider, metric, year)


@app.get("/autocomplete")
async def autocomplete(
    request: Request,
    q: str = Query(min_length=2, max_length=100),
    provider: str = Query(default="camara", pattern="^(camara|senado|executivo|judiciario)$"),
) -> list[Politician]:
    return (await search(request, q, provider))[:8]


@app.get("/politicians/{provider}/{id}")
async def politician(request: Request, provider: str, id: int) -> Politician:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    return await provider_for(request, provider).get(id)


@app.get("/politicians/{provider}/{id}/dashboard")
async def dashboard(request: Request, provider: str, id: int) -> Dashboard:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    return await provider_for(request, provider).dashboard(id)


@app.get("/politicians/{provider}/{id}/context")
async def public_context(request: Request, provider: str, id: int) -> PublicContext:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return context_for(person)


@app.post("/reports/pdf")
async def pdf_report(data: Dashboard) -> Response:
    content = await run_in_threadpool(make_pdf, data)
    filename = (
        f"deputado-{data.politician.id}"
        if data.politician.provider == "camara"
        else f"perfil-{data.politician.id}"
    )
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.pdf"',
            "Cache-Control": "no-store",
        },
    )
