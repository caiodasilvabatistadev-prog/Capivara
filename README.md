# Puxando a Capivara

Consulta Pública

MVP com FastAPI / Python 3.13 e Next.js / TypeScript / Tailwind. Consulta fontes oficiais dos três poderes no âmbito federal, com a cobertura inicial descrita abaixo, sem banco, login, cache ou histórico de buscas.

## Executar

```sh
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install --require-hashes -r requirements-dev.txt
pip install --no-deps -e .
uvicorn app.main:app --reload --no-access-log
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

IDs/providers desconhecidos retornam 404; parâmetros inválidos, 422; fonte indisponível ou resposta inválida, 502. A busca aceita provider=camara|senado|executivo|judiciario (padrão Câmara). /autocomplete usa o mesmo contrato, limitado a 8 sugestões. Não agrega fontes na mesma consulta.

## Qualidade

Backend: `ruff check .`, `ruff format --check .`, `mypy app`, `pytest`. O pytest exige 100% de cobertura de linhas e branches de `app`, com mocks HTTP via respx. Frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npx playwright install chromium`, `npm run e2e` (execute o build antes do E2E). E2E valida o fluxo de interface com API simulada; não é teste de disponibilidade da fonte.

GitHub Actions executa após push/PR e constrói os dois containers após as verificações. Nenhum commit, push ou deploy é automático localmente.

## Estrutura

Rotas chamam providers com uma interface pequena; o provider Câmara concentra HTTP, paginação e normalização. Uma camada de serviço pode ser adicionada quando houver agregação real entre fontes.

Fonte e contrato: https://dadosabertos.camara.leg.br/swagger/api.html

## Railway (preparado, sem deploy)

Crie dois serviços a partir deste repositório com diretórios raiz `backend` e `frontend`; cada um possui Dockerfile. No backend, configure `APP_CORS_ORIGINS` como array JSON contendo o domínio HTTPS do frontend, e healthcheck `/health`. No frontend, configure `NEXT_PUBLIC_API_URL` com o domínio público HTTPS do backend antes do build (é incorporado ao bundle). Os containers respeitam `PORT`; após alterar a URL da API, reconstrua o frontend. Não use o hostname interno do Docker/Railway como URL do navegador.

Não inclua dados sensíveis nas configurações; esta integração não requer chave. `.env.example` documenta variáveis, mas não é carregado automaticamente pelo backend. Configure-as no ambiente do processo.

## Dashboard e PDF

Os perfis da Câmara apresentam gastos, presença, atividade legislativa, recursos e emendas da página principal oficial. As demais fontes mostram os perfis institucionais disponíveis na cobertura inicial. A dashboard permanece no projeto e permite ler todas as seções e baixar um PDF organizado. Não é uma avaliação política nem um registro de candidaturas eleitorais.

`GET /politicians/camara/{id}/dashboard` consulta a API e o perfil público da Câmara. Campos ausentes aparecem como não informados, sem substituir por zero. O ano e as atualizações são os publicados pela fonte. A estrutura HTML pode mudar; páginas inválidas retornam 502.

`POST /reports/pdf` recebe o snapshot da dashboard exibida e retorna um PDF em memória, com download. Não salva arquivos nem pesquisas no servidor. Valores autorizados, empenhados e pagos não são somados. Percentuais originais eventualmente inconsistentes são preservados nas tabelas, mas não usados para notas ou rankings. Páginas vinculadas, vídeos e áudios não são copiados.

O backend permite GET/POST por CORS somente para os domínios configurados. Logs de acesso HTTP ficam desativados no container para não registrar nomes pesquisados.

## Três poderes e busca sugerida

Dark mode, sugestões após 350 ms, cancelamento de requisições anteriores, navegação por setas/Enter/Escape e fotos oficiais (inicial em caso de ausência ou falha). A foto depende da disponibilidade do servidor oficial e não é armazenada.

Cobertura federal inicial: Legislativo (Câmara e senadores em exercício), Executivo (titulares da Saúde e Fazenda) e Judiciário (ministros em atividade do STJ). Não cobre todos os órgãos, STF, presidência, estados ou municípios. As fontes do Planalto bloquearam acesso automático e o STF não estava acessível neste ambiente; não foram substituídas por listas fictícias ou desatualizadas.

Senado: https://legis.senado.leg.br/dadosabertos/senador/lista/atual.json
STJ: https://www.stj.jus.br/web/verMinistrosSTJ?parametro=1
Executivo: páginas de composição oficiais dos ministérios. IDs internos 1 e 2 identificam as pastas Saúde e Fazenda, resolvendo seu titular a cada consulta; não são identificadores governamentais de pessoas. Os perfis novos incluem cargo, órgão e contatos/currículo disponíveis, sem indicadores parlamentares inventados. Ausência de fonte válida retorna erro 502.

## Notícias e situação judicial

A dashboard consulta registros editoriais revisados pelo botão da seção; não classifica pessoas por manchetes e não faz coleta automática nem monitoramento processual. A API /politicians/{provider}/{id}/context valida a identidade na fonte governamental antes de associar registros por provider, ID e nome. Sem registro revisado, informa ausência de cobertura; nunca afirma inexistência de condenações.

Curadoria inicial em app/editorial.py, versionada no Git: primeiro perfil Sergio Moro (Senado 6331), com ação eleitoral julgada improcedente em maio/2024 e Lei 15.245/2025. Não são exemplos fictícios nem uma ficha completa; estados históricos têm data explícita e fonte oficial/jornalística. Nenhuma acusação de corrupção foi cadastrada sem comprovação. Os outros perfis não têm registros editoriais revisados nesta primeira versão.

Estados aceitos: condenação definitiva (exige trânsito em julgado), condenação recorrível, em andamento, absolvido, arquivado, anulado e pedido rejeitado. Todo caso exige tribunal, processo, data e URL oficial .jus.br, além de referência jornalística. Uma improcedência eleitoral não é rotulada como absolvição criminal. Ações distinguem proposta, aprovada e execução documentada; autoria não presume crédito exclusivo nem impacto comprovado.

Para ampliar a cobertura, revisar documentação por perfil e cadastrar fontes, contexto e datas com os mesmos critérios, independentemente de partido; registrar revisões e correções no histórico do Git. Este fluxo é editorial, sem IA inferindo culpa e sem scraping de artigos completos. O PDF inclui os registros e fontes consultados na tela quando a seção foi carregada.

## Dashboards por poder

O mesmo componente apresenta perfil, gastos, atividade, agenda/presença, recursos, emendas e contexto judicial, adaptando os rótulos ao cargo. Campos sem fonte aparecem como não disponíveis; indicadores parlamentares incompatíveis são marcados como não aplicáveis. Não há números fictícios nem imputação de orçamento institucional como gasto pessoal.

Senado: perfil público (dados pessoais, suplentes, comissões, missões e biografia) e prestação de contas do ano corrente (CEAPS por categoria, despesas fora da CEAPS, benefícios e equipe). Mantém tabelas, fontes e datas no PDF. Falha de uma página complementar preserva o perfil e informa a fonte indisponível; não transforma falha em zero. Produção legislativa, votos, presença, emendas, remuneração e detalhamento mensal ainda não estão integrados.

Executivo: currículo, trajetória e contatos da autoridade; áreas comuns de gastos, remuneração, agenda e atuação informam limites. A agenda e-Agendas exige token (documentação CGU: https://github.com/cgugovbr/eagendas-publico/tree/main/api-consulta). Não captura a agenda pela página de filtro, que depende de aplicação dinâmica. Remuneração exige outra integração no Portal da Transparência.

Judiciário: currículo dividido pelas seções oficiais e funções atuais destacadas, incluindo formação e trajetória; mantém o conteúdo completo do currículo consultado. Decisões, produtividade, remuneração e agenda não estão integradas. A cobertura institucional continua sendo STJ, Saúde e Fazenda, além do Senado e Câmara; não inclui todos os órgãos ou todas as autoridades.

## Comparações abaixo da busca

GET /rankings?provider=camara|senado|executivo|judiciario&metric=expenses|absences|approved|party_fund|election_fund&year=2026 retorna fontes, período, cobertura e estados ready/partial/unavailable/not_applicable. UI acompanha o poder/casa selecionado. Consultas são manuais por lista; sem banco, persistência ou cache de pesquisas. Não há nota política.

Gastos: arquivos anuais CEAP (Câmara, coluna vlrLiquido) e CEAPS (Senado, valorReembolsado, IDs duplicados ignorados). Decimais exatos no cálculo. Câmara exclui registros de lideranças sem ideCadastro; inclui registros de pessoas fora de exercício hoje. Não reúne salário, verba de gabinete ou todos os custos; não compara casas. Não aplica ajustes de restituição registrados em outras colunas. Empates têm a mesma posição e a exibição limita-se a dez entradas.

Ausências: consulta perfis da Câmara com concorrência limitada a oito e prazo de 180 segundos, exigindo o ano solicitado e os dois contadores publicados de ausência em Plenário. Soma justificadas e não justificadas, mantendo ambas na descrição; não mistura com comissões, não infere faltas de votos. Dados faltantes e falhas contam como cobertura incompleta, sem zero inventado. Ranking parcial refere-se somente aos perfis consultados. Senado sem fonte de faltas integrada; Executivo/Judiciário exigem outras métricas.

Projetos aprovados: ainda indisponível, até levantar aprovação final e autoria validada no período. Não substitui por projetos apresentados, votações ou requerimentos aprovados.

Fundos: independentes do poder, nacionais. Curadoria dos cinco maiores repasses do Fundo Partidário no balanço TSE de 2025 (dotação + multas), e de todos os 30 valores destinados no FEFC 2026 (não comprova recebimento por candidaturas). Fontes oficiais e data de publicação na resposta; revisão manual em 18/09/2026. A coleta direta do TSE retornou 403 neste ambiente; snapshots não se apresentam como atualização automática e não são extrapolados para outros anos.
