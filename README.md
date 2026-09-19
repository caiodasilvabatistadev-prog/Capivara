# Puxando a Capivara

Plataforma de transparência e educação política que centraliza dados públicos para ajudar
o eleitor a votar melhor, reconhecer quem recebeu seu voto e entender como a política
brasileira funciona. O produto reúne fontes que hoje estão espalhadas por diferentes
órgãos, preserva o contexto e explica termos técnicos em linguagem simples.

MVP com FastAPI / Python 3.13 e Next.js / TypeScript / Tailwind. Consulta fontes oficiais dos três poderes no âmbito federal, com a cobertura inicial descrita abaixo, sem banco, login, cache ou histórico de buscas.

## Objetivo e compromisso editorial

O Puxando a Capivara aproxima a população dos dados públicos. Cada perfil procura responder
perguntas concretas: quem é essa pessoa, qual cargo ocupa, como atua, quanto gasta, quais
propostas apresentou ou relatou, como votou, para onde destinou emendas e quais fatos
judiciais possuem documentação verificável.

O projeto não cria pontuação política, recomenda voto ou presume culpa. Fonte, período e
limites de cobertura acompanham os indicadores. Reportagem fornece contexto; condenação,
absolvição, inelegibilidade e situação prisional exigem documentação oficial apropriada.

## Funcionalidades entregues

- Busca única com autocomplete, fotos e identificação por cargo, partido, estado e poder.
- Perfis de deputados, senadores, governadores, autoridades do Executivo e Judiciário e
  candidaturas encontradas nas bases integradas.
- Dashboard com biografia, profissão, cargos anteriores, presença, gastos, equipe, benefícios,
  emendas, votações e notícias relacionadas.
- Propostas de autoria e propostas relatadas, listadas individualmente com explicação simples,
  descrição original, situação e fonte oficial.
- Profissões como tags clicáveis que abrem políticos em exercício com a mesma profissão.
- Bens declarados à Justiça Eleitoral, com ano, descrição, valor e aviso de que a declaração
  não representa necessariamente o patrimônio atual.
- PDF completo do perfil sem retirar o usuário do projeto.
- Rankings de gastos, faltas, projetos, emendas, Fundo Partidário e Fundo Eleitoral, respeitando
  a cobertura de cada fonte.
- Composição partidária da Câmara e do Senado, gráficos e distribuição de cadeiras.
- Sexo e raça/cor autodeclarados nas candidaturas do TSE, sem inferência por nome ou fotografia.
- Árvores de famílias políticas somente com parentescos documentados.
- Página Fichas sujas com decisões eleitorais, condenações e regimes prisionais confirmados.
- Guia Como funciona, do vereador ao STF, incluindo mandatos, deveres, limites, sistema
  proporcional, quocientes e efeito dos votos dados ao partido ou federação.
- Glossário acessível para termos difíceis.
- Página de fontes, compartilhamento e inscrição confirmada por e-mail.
- Dark mode, interface responsiva e fotografias junto das referências a pessoas.

## Por que esta tecnologia

- **Python 3.13:** mantém integrações, normalização e análise de dados legíveis, com um amplo
  ecossistema para HTTP, arquivos públicos e PDFs.
- **FastAPI:** oferece API assíncrona, validação e documentação automática com pouco código
  repetido. Isso permite consultar várias fontes sem transformar o MVP em uma arquitetura
  difícil de manter.
- **HTTPX e Pydantic:** HTTP assíncrono e contratos de dados validados antes de chegar à tela.
- **Beautiful Soup:** interpreta páginas oficiais quando o órgão ainda não oferece o dado em
  uma API estruturada.
- **ReportLab:** cria o relatório PDF inteiramente no servidor e sem salvar a pesquisa.
- **Next.js 16 e React 19:** páginas rápidas, componentes reutilizáveis e uma base preparada
  para SEO e compartilhamento público.
- **TypeScript:** reduz erros entre o formato enviado pela API e o que a interface apresenta.
- **Tailwind CSS 4:** mantém o design responsivo e consistente sem repetir grandes folhas de
  estilo.
- **Pytest, pytest-cov e respx:** verificam regras e integrações com respostas controladas;
  o backend só passa com 100% de cobertura de linhas e branches.
- **Vitest e Testing Library:** validam os componentes pelo comportamento percebido pelo
  usuário.
- **Playwright:** testa os fluxos completos de busca, consulta e navegação.
- **Ruff e mypy:** asseguram padronização e tipagem estrita no backend.
- **Docker e Docker Compose:** garantem que o mesmo artefato seja usado localmente, no CI e
  em produção.
- **GitHub Actions:** bloqueia a construção dos contêineres quando lint, tipos ou testes falham.
- **Railway:** simplifica o primeiro deploy dos dois serviços, healthcheck, variáveis e domínio
  HTTPS sem exigir a operação imediata de uma infraestrutura própria.

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

Transferências Especiais (Emendas Pix): a ficha de deputados e senadores consulta os
planos de ação e empenhos publicados pelo Transferegov, por nome do parlamentar e ano.
Exibe ente beneficiário, UF, área da política pública, valor planejado, valor empenhado,
situação e identificação oficial. Plano, empenho e pagamento são etapas distintas; o
campo pago não é preenchido quando o endpoint consultado não comprova a ordem bancária.
Fonte e contrato:
https://docs.api.transferegov.gestao.gov.br/transferenciasespeciais/

O glossário da interface explica termos técnicos após um segundo de permanência do mouse
e também funciona por foco do teclado. As definições ficam centralizadas no componente
GlossaryTerm.

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

Senado: perfil público (dados pessoais, suplentes, comissões, missões e biografia), prestação de contas do ano corrente (CEAPS por categoria, despesas fora da CEAPS, benefícios e equipe), votos nominais e Transferências Especiais (Emendas Pix). Mantém tabelas, fontes e datas no PDF. Falha de uma página complementar preserva o perfil e informa a fonte indisponível; não transforma falha em zero. Produção legislativa, presença, demais modalidades de emenda, remuneração e detalhamento mensal ainda não estão integrados.

Executivo: currículo, trajetória e contatos da autoridade; áreas comuns de gastos, remuneração, agenda e atuação informam limites. A agenda e-Agendas exige token (documentação CGU: https://github.com/cgugovbr/eagendas-publico/tree/main/api-consulta). Não captura a agenda pela página de filtro, que depende de aplicação dinâmica. Remuneração exige outra integração no Portal da Transparência.

Judiciário: currículo dividido pelas seções oficiais e funções atuais destacadas, incluindo formação e trajetória; mantém o conteúdo completo do currículo consultado. Decisões, produtividade, remuneração e agenda não estão integradas. A cobertura institucional continua sendo STJ, Saúde e Fazenda, além do Senado e Câmara; não inclui todos os órgãos ou todas as autoridades.

## Comparações abaixo da busca

GET /rankings?provider=camara|senado|executivo|judiciario&metric=expenses|absences|approved|party_fund|election_fund&year=2026 retorna fontes, período, cobertura e estados ready/partial/unavailable/not_applicable. A comparação parlamentar possui sua própria seleção de Câmara ou Senado. Consultas são manuais por lista; sem banco, persistência ou cache de pesquisas. Não há nota política.

Gastos: arquivos anuais CEAP (Câmara, coluna vlrLiquido) e CEAPS (Senado, valorReembolsado, IDs duplicados ignorados). Decimais exatos no cálculo. Câmara exclui registros de lideranças sem ideCadastro; inclui registros de pessoas fora de exercício hoje. Não reúne salário, verba de gabinete ou todos os custos; não compara casas. Não aplica ajustes de restituição registrados em outras colunas. Empates têm a mesma posição e a exibição limita-se a dez entradas.

Ausências: consulta perfis da Câmara com concorrência limitada a oito e prazo de 180 segundos, exigindo o ano solicitado e os dois contadores publicados de ausência em Plenário. Soma justificadas e não justificadas, mantendo ambas na descrição; não mistura com comissões, não infere faltas de votos. Dados faltantes e falhas contam como cobertura incompleta, sem zero inventado. Ranking parcial refere-se somente aos perfis consultados. Senado sem fonte de faltas integrada; Executivo/Judiciário exigem outras métricas.

Projetos aprovados: ainda indisponível, até levantar aprovação final e autoria validada no período. Não substitui por projetos apresentados, votações ou requerimentos aprovados.

Fundos: independentes do poder, nacionais. Curadoria dos cinco maiores repasses do Fundo Partidário no balanço TSE de 2025 (dotação + multas), e de todos os 30 valores destinados no FEFC 2026 (não comprova recebimento por candidaturas). Fontes oficiais e data de publicação na resposta; revisão manual em 18/09/2026. A coleta direta do TSE retornou 403 neste ambiente; snapshots não se apresentam como atualização automática e não são extrapolados para outros anos.

### Busca automática de notícias

Ao abrir um perfil, `/politicians/{provider}/{id}/news` resolve o nome na fonte oficial e consulta o RSS de busca do Google Notícias, limitado a G1, Folha, Estadão, UOL, CNN Brasil, Poder360 e Intercept Brasil. Filtra localmente o nome completo e os termos no título, valida o domínio do veículo, remove títulos duplicados e retorna até 20 itens por data. Sem banco, cache ou coleta periódica. A indexação é parcial; homônimos e menções a terceiros podem existir. Não extrai artigos, contorna assinaturas ou determina situação judicial por palavras-chave. Exibe títulos, datas e referências dentro do produto, separado da curadoria judicial. Não inventa resumos a partir do título; resultados automáticos não entram no PDF como registros revisados.

### Emendas e votos individuais

Detalhamento sob consulta na dashboard, incluído no PDF após carregado. Câmara: página oficial `todas-emendas` com paginação (até 20 páginas), finalidade/localidade/órgão publicados e valores por etapa. Isso não identifica necessariamente o recebedor final; detalhamento documental de beneficiários pela CGU ainda não integrado. Senado: API atual `/dadosabertos/votacao`, sem usar serviço legado, com filtro de parlamentar e ano e intervalo aplicado localmente. Câmara: até 100 eventos recentes de Plenário no intervalo, listas nominais e objetos possíveis como contexto; não substitui a descrição da etapa. Votações simbólicas não têm voto individual inferido. Dados sem registro não são faltas; voto secreto não tem posição revelada. Intervalos de 30, 90 ou 365 dias e filtros textuais por assunto, sem juízo de qualidade ou ranking. Destinos de emendas do Senado ainda não integrados; indicadores parlamentares não se aplicam ao Executivo/Judiciário. Nenhum armazenamento ou cache.


### Partidos e presidências
As duas listas de fundos exibem logos e a presidência nacional dos dez partidos apresentados. Nomes conferidos no cadastro de partidos registrados do TSE em 18/09/2026; atualização manual. Links abrem perfis internos de presidência partidária, com fonte e limites, sem presumir candidatura ou mandato. Os fundos pertencem ao partido, não ao presidente pessoalmente. Logos locais mantêm suas marcas originais; fontes em `frontend/public/parties/SOURCES.md`.

### Ajustes do banner e compartilhamento

A página inicial usa uma única barra de busca, sem exigir que a pessoa conheça previamente o poder ou o órgão. Cada resultado identifica cargo, partido publicado, poder e UF. Buscar ocupa uma linha abaixo do nome. A ilustração acompanha a altura do formulário no computador e aparece em bloco próprio no celular. As 26 estrelas são elementos SVG decorativos, com quantidade determinística.

O header oferece compartilhamento por WhatsApp e X, com texto e URL do domínio publicado. Instagram utiliza o compartilhamento nativo do dispositivo, quando disponível, ou copia texto e link para colagem manual; não publica automaticamente. Em localhost, essas opções ficam desabilitadas com explicação de que é necessário publicar o site.

Arte editada com a ferramenta integrada de geração de imagens: `frontend/public/capivara-tres-poderes-v2.png`. A versão original foi preservada. Prompt: corrigir somente a perspectiva física do binóculo, com tubos paralelos ligados por ponte coerente, elipses das lentes no mesmo plano, oculares alinhadas aos olhos e mãos segurando o mesmo corpo rígido; preservar capivara, camisa amarela, arquitetura, cores, composição e céu vazio, sem texto. As estrelas são acrescentadas pela interface.


## Busca unificada, governadores e candidaturas

`GET /search/all?q=nome` e `GET /autocomplete/all?q=nome` consultam Câmara, Senado, ministérios, STJ, governadores e adaptadores do TSE em paralelo. A resposta inclui o resultado de cada fonte; falhas não escondem registros das demais e nunca são apresentadas como uma busca completa. Resultados mantêm registros separados por fonte e ID para não fundir homônimos nem confundir candidatura com cargo atual.

Governadores: a integração consulta sob demanda o cadastro público `https://www.governo.mg.gov.br/api/MundoOficial/consulta?categoriaId=18`. A fonte retornou os 26 estados e o Distrito Federal na validação de 18/09/2026. A dashboard reproduz os campos publicados e situações interinas; partido, foto, patrimônio, gastos e orçamento aparecem como não informados pela fonte, sem inferência ou zero fictício.

Candidaturas: os adaptadores leem em memória os arquivos oficiais `consulta_cand_2026.zip` e `consulta_cand_2024.zip`, sem banco ou armazenamento de pesquisas. O frontend informa quando os arquivos do TSE estiverem indisponíveis. Registros mostram explicitamente o ano e não comprovam mandato nem filiação atual. CPF, título eleitoral e e-mail particular não são exibidos ou exportados. Neste ambiente, o CDN do TSE respondeu com acesso negado durante a validação; portanto, a cobertura de qualquer candidatura ainda depende da disponibilidade dessa fonte pública.

## Guia “Como a política funciona”

A rota `/como-funciona` explica os três poderes, funções, deveres, limites, forma de escolha e duração dos cargos de vereador a ministro do STF. Também diferencia eleição majoritária e proporcional, descreve quocientes e sobras com limites explícitos e mostra por que votos de uma candidatura podem ajudar outras do mesmo partido ou federação. O texto referencia Constituição Federal, Lei Complementar 152/2015, TSE e Câmara dos Deputados e informa que é um guia introdutório.
