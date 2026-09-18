# Capivara

Consulta Pública

MVP com FastAPI / Python 3.13 e Next.js / TypeScript / Tailwind. Consulta a API oficial da Câmara, sem banco, login, cache ou histórico de buscas.

## Executar

```sh
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install --require-hashes -r requirements-dev.txt
pip install --no-deps -e .
uvicorn app.main:app --reload
```

Em outro terminal:

```sh
cd frontend
npm ci
npm run dev
```

Frontend: http://localhost:3000. API/documentação: http://localhost:8000/docs.

Ou, na raiz: `docker compose up --build`.

## Endpoints

- `GET /health`: saúde do processo (não consulta a Câmara).
- `GET /search?q=Maria`: busca por nome, paginação interna até o fim dos resultados.
- `GET /politicians/camara/1`: perfil pelo identificador oficial.

IDs/providers desconhecidos retornam 404; parâmetros inválidos, 422; fonte indisponível ou resposta inválida, 502. A busca consulta deputados conforme os filtros padrão da Câmara; não agrega Senado nem outras esferas neste MVP.

## Qualidade

Backend: `ruff check .`, `ruff format --check .`, `mypy app`, `pytest`. O pytest exige 100% de cobertura de linhas e branches de `app`, com mocks HTTP via respx. Frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npx playwright install chromium`, `npm run e2e` (execute o build antes do E2E). E2E valida o fluxo de interface com API simulada; não é teste de disponibilidade da fonte.

GitHub Actions executa após push/PR e constrói os dois containers após as verificações. Nenhum commit, push ou deploy é automático localmente.

## Estrutura

Rotas chamam providers com uma interface pequena; o provider Câmara concentra HTTP, paginação e normalização. Uma camada de serviço pode ser adicionada quando houver agregação real entre fontes.

Fonte e contrato: https://dadosabertos.camara.leg.br/swagger/api.html

## Railway (preparado, sem deploy)

Crie dois serviços a partir deste repositório com diretórios raiz `backend` e `frontend`; cada um possui Dockerfile. No backend, configure `APP_CORS_ORIGINS` como array JSON contendo o domínio HTTPS do frontend, e healthcheck `/health`. No frontend, configure `NEXT_PUBLIC_API_URL` com o domínio público HTTPS do backend antes do build (é incorporado ao bundle). Os containers respeitam `PORT`; após alterar a URL da API, reconstrua o frontend. Não use o hostname interno do Docker/Railway como URL do navegador.

Não inclua dados sensíveis nas configurações; esta integração não requer chave. `.env.example` documenta variáveis, mas não é carregado automaticamente pelo backend. Configure-as no ambiente do processo.
