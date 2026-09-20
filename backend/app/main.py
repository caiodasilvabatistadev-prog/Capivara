from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.concurrency import run_in_threadpool

from app.assets import AssetDisclosure, declared_assets
from app.biography import Biography, wikipedia_biography
from app.career import Career, ProfessionMatch, official_career, people_by_profession
from app.composition import HouseComposition, composition
from app.dashboard import Dashboard, ReportSection
from app.directories import ExecutiveProvider, JudicialProvider, SenateProvider
from app.editorial import PublicContext, context_for
from app.elections import DemographicSnapshot, ElectionProvider
from app.family import PoliticalFamily, documented_family
from app.governors import GovernorProvider
from app.models import Politician
from app.news import NewsResult, search_news
from app.parliament import amendments, proposals, votes
from app.parties import PartyProvider
from app.pdf_report import make_pdf
from app.providers import CamaraProvider, Provider
from app.public_figures import PRESIDENTS, STF_FIGURES, CatalogProvider, HistoricalCamaraProvider
from app.rankings import MetricName, Ranking, ranking
from app.subscriptions import (
    MailSettings,
    SubscriptionRequest,
    SubscriptionResponse,
    confirm_subscription,
    create_subscription,
    initialize_database,
    send_confirmation,
)
from app.universal_search import SearchResult, universal_search


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")
    cors_origins: list[str] = ["http://localhost:3000"]
    database_path: str = "data/subscriptions.sqlite3"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_sender: str = ""
    notification_email: str = ""
    transparency_api_key: str = ""
    public_url: str = "http://localhost:3000"

    def mail(self) -> MailSettings:
        return MailSettings(
            host=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_username,
            password=self.smtp_password,
            sender=self.smtp_sender,
            notification_email=self.notification_email,
            public_url=self.public_url,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    initialize_database(settings.database_path)
    app.state.settings = settings
    async with httpx.AsyncClient(
        base_url="https://dadosabertos.camara.leg.br/api/v2/",
        timeout=15,
        headers={"Accept": "application/json"},
    ) as client:
        app.state.http_client = client
        app.state.providers = {
            "camara": CamaraProvider(client),
            "partidos": PartyProvider(),
            "senado": SenateProvider(client),
            "executivo": ExecutiveProvider(client),
            "judiciario": JudicialProvider(client),
            "governadores": GovernorProvider(client),
            "stf": CatalogProvider(client, "stf", STF_FIGURES),
            "presidentes": CatalogProvider(client, "presidentes", PRESIDENTS),
            "camara_historica": HistoricalCamaraProvider(client),
            "tse2026": ElectionProvider(client, 2026),
            "tse2024": ElectionProvider(client, 2024),
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


@app.get("/composition/{provider}")
async def house_composition(
    request: Request, provider: Literal["camara", "senado"]
) -> HouseComposition:
    return await composition(provider_for(request, provider), provider)


@app.get("/politicians/{provider}/{id}/biography")
async def politician_biography(request: Request, provider: str, id: int) -> Biography:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await wikipedia_biography(request.app.state.http_client, person)


@app.get("/politicians/{provider}/{id}/family")
async def politician_family(request: Request, provider: str, id: int) -> PoliticalFamily:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await documented_family(request.app.state.http_client, person)


@app.get("/politicians/{provider}/{id}/career")
async def politician_career(request: Request, provider: str, id: int) -> Career:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await official_career(request.app.state.http_client, person)


@app.get("/professions")
async def profession_people(
    request: Request, name: str = Query(min_length=2, max_length=100)
) -> ProfessionMatch:
    return await people_by_profession(request.app.state.http_client, name)


@app.get("/politicians/{provider}/{id}/assets")
async def politician_assets(request: Request, provider: str, id: int) -> AssetDisclosure:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await declared_assets(request.app.state.http_client, person)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demographics")
async def demographics(
    request: Request, year: Literal["2024", "2026"] = "2024"
) -> DemographicSnapshot:
    provider = provider_for(request, f"tse{year}")
    if not isinstance(provider, ElectionProvider):
        raise HTTPException(404, "Base eleitoral não encontrada")
    return await provider.demographics()


@app.post("/subscriptions", status_code=201)
async def subscribe(data: SubscriptionRequest, request: Request) -> SubscriptionResponse:
    settings: Settings = request.app.state.settings
    token, confirmed = await run_in_threadpool(create_subscription, settings.database_path, data)
    if confirmed:
        return SubscriptionResponse(
            message="Este alerta já está confirmado.", confirmation_required=False
        )
    subject = (
        f"Confirme o alerta sobre {data.politician_name}"
        if data.politician_name
        else "Confirme as novidades do Puxando a Capivara"
    )
    sent = await run_in_threadpool(
        send_confirmation, settings.mail(), str(data.email), token, subject
    )
    message = (
        "Enviamos um link de confirmação para o seu e-mail."
        if sent
        else "Inscrição registrada. O envio da confirmação será ativado após configurar o e-mail."
    )
    return SubscriptionResponse(message=message)


@app.get("/subscriptions/confirm/{token}")
async def confirm(token: str, request: Request) -> SubscriptionResponse:
    if len(token) < 20:
        raise HTTPException(404, "Confirmação inválida")
    settings: Settings = request.app.state.settings
    confirmed = await run_in_threadpool(confirm_subscription, settings.database_path, token)
    if not confirmed:
        raise HTTPException(404, "Confirmação inválida")
    return SubscriptionResponse(
        message="E-mail confirmado. Você receberá os alertas escolhidos.",
        confirmation_required=False,
    )


@app.get("/search")
async def search(
    request: Request,
    q: str = Query(min_length=2, max_length=100),
    provider: str = Query(
        default="camara",
        pattern="^(camara|senado|executivo|judiciario|governadores|stf|presidentes|camara_historica)$",
    ),
) -> list[Politician]:
    name = q.strip()
    if len(name) < 2:
        raise HTTPException(422, "Informe pelo menos dois caracteres")
    return await provider_for(request, provider).search(name)


@app.get("/search/all")
@app.get("/autocomplete/all")
async def search_all(
    request: Request, q: str = Query(min_length=2, max_length=100)
) -> SearchResult:
    name = q.strip()
    if len(name) < 2:
        raise HTTPException(422, "Informe pelo menos dois caracteres")
    return await universal_search(
        request.app.state.providers, name, 8 if "autocomplete" in request.url.path else None
    )


@app.get("/rankings")
async def public_rankings(
    request: Request,
    provider: str = Query(
        default="camara",
        pattern="^(camara|senado|executivo|judiciario|governadores|stf|presidentes|camara_historica)$",
    ),
    metric: MetricName = "expenses",
    year: int = Query(default=datetime.now(UTC).year, ge=2024, le=datetime.now(UTC).year),
) -> Ranking:
    source = provider_for(request, provider)
    settings: Settings = request.app.state.settings
    return await ranking(
        request.app.state.http_client,
        source,
        provider,
        metric,
        year,
        settings.transparency_api_key,
    )


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


@app.get("/politicians/{provider}/{id}/news")
async def politician_news(request: Request, provider: str, id: int) -> NewsResult:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await search_news(request.app.state.http_client, person.name)


@app.get("/politicians/{provider}/{id}/amendments")
async def amendment_destinations(
    request: Request,
    provider: str,
    id: int,
    year: int = Query(default=datetime.now(UTC).year, ge=2024, le=datetime.now(UTC).year),
) -> ReportSection:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await amendments(request.app.state.http_client, person, year)


@app.get("/politicians/{provider}/{id}/proposals")
async def authored_proposals(
    request: Request,
    provider: str,
    id: int,
    year: int = Query(default=datetime.now(UTC).year, ge=2000, le=datetime.now(UTC).year),
    kind: Literal["authored", "reported"] = "authored",
) -> ReportSection:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    person = await provider_for(request, provider).get(id)
    return await proposals(request.app.state.http_client, person, year, kind == "reported")


@app.get("/politicians/{provider}/{id}/votes")
async def individual_votes(
    request: Request, provider: str, id: int, days: int = Query(default=90, ge=1, le=365)
) -> ReportSection:
    if id < 1:
        raise HTTPException(422, "ID deve ser positivo")
    await provider_for(request, provider).get(id)
    return await votes(request.app.state.http_client, provider, id, days)
