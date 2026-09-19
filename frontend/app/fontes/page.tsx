import Header from "../../components/Header";

const groups = [
  { title: "Dados governamentais e parlamentares", sources: [
    ["Câmara dos Deputados — Dados Abertos", "https://dadosabertos.camara.leg.br/swagger/api.html", "Deputados, perfis, profissões, mandatos anteriores, despesas, presença, propostas, votações e composição partidária."],
    ["Senado Federal — Dados Abertos", "https://www12.senado.leg.br/dados-abertos", "Senadores em exercício, perfis, votações, composição e informações parlamentares disponíveis."],
    ["Transparência do Senado", "https://www6g.senado.leg.br/transparencia/", "Recursos, equipe e informações administrativas publicadas para senadores."],
    ["Transferegov — Transferências Especiais", "https://docs.api.transferegov.gestao.gov.br/transferenciasespeciais/", "Emendas Pix, beneficiários, finalidade declarada e etapas financeiras."],
    ["Portal da Transparência", "https://portaldatransparencia.gov.br/api-de-dados", "Referência para despesas, recursos federais e futuras integrações de transparência."],
    ["STJ — Ministros", "https://www.stj.jus.br/web/verMinistrosSTJ?parametro=1", "Relação e perfis públicos de ministros do Superior Tribunal de Justiça."],
    ["Gov.br — Ministério da Saúde", "https://www.gov.br/saude/pt-br/composicao/ministro", "Perfil institucional da autoridade responsável pelo ministério."],
    ["Gov.br — Ministério da Fazenda", "https://www.gov.br/fazenda/pt-br/composicao/ministro", "Perfil institucional da autoridade responsável pelo ministério."],
    ["Mundo Oficial — Governadores", "https://www.governo.mg.gov.br/mundo-oficial", "Cadastro público dos governadores dos 26 estados e do Distrito Federal."],
  ] },
  { title: "Processos e situação judicial", sources: [
    ["STF — Consulta Processual", "https://portal.stf.jus.br/processos/", "Pesquisa processos no Supremo por nome da parte, número, classe, origem ou advogado."],
    ["STJ — Consulta Processual", "https://www.stj.jus.br/sites/portalp/Processos/Consulta-Processual", "Acompanha fases e decisões no STJ; processos sigilosos possuem acesso limitado."],
    ["Justiça Eleitoral — Consulta Pública PJe", "https://www.tse.jus.br/servicos-judiciais/processos/pje", "Processos eleitorais das zonas eleitorais, TREs e TSE."],
    ["CNJ — API Pública DataJud", "https://datajud-wiki.cnj.jus.br/api-publica/acesso/", "Metadados de processos públicos, consultados por endpoints próprios de cada tribunal."],
  ] },
  { title: "Dados eleitorais e partidos", sources: [
    ["TSE — Portal de Dados Abertos", "https://dadosabertos.tse.jus.br/", "Candidaturas, eleições, sexo, raça/cor e ocupação autodeclarados nos arquivos eleitorais."],
    ["TSE — Partidos registrados", "https://www.tse.jus.br/partidos/partidos-registrados-no-tse", "Siglas, registros partidários e dirigentes publicados."],
    ["TSE — Fundo Partidário", "https://www.tse.jus.br/comunicacao/noticias/2026/Janeiro/fundo-partidario-19-partidos-receberam-mais-de-r-1-bilhao-em-2025", "Valores anuais usados na comparação do Fundo Partidário."],
    ["TSE — Fundo Eleitoral", "https://www.tse.jus.br/eleicoes/eleicoes-2026-content/prestacao-de-contas/distribuicao-dos-recursos-do-fundo-especial-de-financiamento-de-campanha-fefc-eleicoes-2026", "Valores destinados aos partidos para o Fundo Eleitoral."],
  ] },
  { title: "Biografia e parentescos documentados", sources: [
    ["Wikipédia em português", "https://pt.wikipedia.org/", "Resumo complementar quando o título corresponde exatamente ao nome consultado."],
    ["Wikidata", "https://www.wikidata.org/", "Parentescos exibidos somente quando a declaração possui referência cadastrada."],
    ["FGV CPDOC — DHBB", "https://cpdoc.fgv.br/acervo/dicionarios/dhbb", "Referência histórica planejada para trajetórias, ex-políticos e famílias políticas."],
  ] },
  { title: "Notícias e contexto jornalístico", sources: [
    ["Google Notícias — índice RSS", "https://news.google.com/", "Localiza títulos nas fontes selecionadas; pode omitir resultados ou trazer homônimos."],
    ["G1", "https://g1.globo.com/", "Veículo selecionado para contexto jornalístico."],
    ["Folha de S.Paulo", "https://www.folha.uol.com.br/", "Veículo selecionado para contexto jornalístico."],
    ["Estadão", "https://www.estadao.com.br/", "Veículo selecionado para contexto jornalístico."],
    ["UOL", "https://www.uol.com.br/", "Veículo selecionado para contexto jornalístico."],
    ["CNN Brasil", "https://www.cnnbrasil.com.br/", "Veículo selecionado para contexto jornalístico."],
    ["Poder360", "https://www.poder360.com.br/", "Veículo selecionado para contexto jornalístico."],
    ["Intercept Brasil", "https://www.intercept.com.br/", "Veículo selecionado para contexto jornalístico."],
  ] },
];

export default function SourcesPage() {
  return <><Header /><main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Transparência da própria plataforma</p>
    <h1 className="mt-2 text-4xl font-bold">Todas as fontes do projeto</h1>
    <p className="mt-4 max-w-4xl leading-relaxed text-slate-600">Veja de onde vem cada informação, o que ela sustenta e quais limites permanecem. Fonte jornalística dá contexto; situação judicial exige documento ou fonte oficial. Ausência de registro não comprova ausência do fato.</p>
    {groups.map(group => <section className="mt-12" aria-labelledby={`source-${group.title}`} key={group.title}><h2 id={`source-${group.title}`} className="text-2xl font-bold">{group.title}</h2><div className="mt-5 grid gap-4 md:grid-cols-2">{group.sources.map(([name, url, coverage]) => <article className="rounded-2xl border bg-white p-5" key={name}><h3 className="text-lg font-bold">{name}</h3><p className="mt-3 text-sm leading-relaxed text-slate-600">{coverage}</p><a className="mt-4 inline-block break-all text-sm font-semibold text-emerald-800 underline" href={url} target="_blank" rel="noreferrer">Consultar fonte</a></article>)}</div></section>)}
    <section className="mt-12 rounded-2xl border bg-white p-6"><h2 className="text-2xl font-bold">PDFs enviados ao projeto</h2><p className="mt-3 text-sm leading-relaxed text-slate-600">Documentos enviados podem complementar um perfil quando identificamos autoria, data, páginas relevantes e origem. Eles não substituem a confirmação oficial. Alegações, investigações, processos, absolvições e condenações são apresentados como estados diferentes.</p></section>
  </main></>;
}
