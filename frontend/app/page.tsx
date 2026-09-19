"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import Header from "../components/Header";
import Dashboard from "../components/Dashboard";
import Newsletter from "../components/Newsletter";
import Portrait from "../components/Portrait";
import { type Politician, type DashboardData, type SearchResult, type SearchSource, request } from "../lib/api";

const powers: Record<string, string> = { legislativo: "Legislativo", executivo: "Executivo", judiciario: "Judiciário", partidario: "Partidário" };
function identity(person: Politician) { return `${person.role || "Deputado federal"} · ${person.party} · ${powers[person.power || "legislativo"] || person.power} · ${person.state}`; }
export default function Home() {
  const [sources, setSources] = useState<SearchSource[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Politician[] | null>(null);
  const [selected, setSelected] = useState<DashboardData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState<Politician[]>([]);
  const [focused, setFocused] = useState(false);
  const [active, setActive] = useState(-1);
  const [suggestionStatus, setSuggestionStatus] = useState("");
  useEffect(() => {
    if (!focused || busy || query.trim().length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSuggestionStatus("Buscando sugestões…");
      try {
        const data = await request<SearchResult>("/autocomplete/all?q=" + encodeURIComponent(query.trim()), controller.signal);
        if (!controller.signal.aborted) {
          const matches = data.items;
          setSources(data.sources);
          setSuggestions(matches); setActive(-1);
          setSuggestionStatus(matches.length ? "" : "Nenhuma sugestão encontrada. Você pode tentar outra busca.");
        }
      } catch {
        if (!controller.signal.aborted) setSuggestionStatus("Sugestões indisponíveis. Tente o botão Buscar.");
      }
    }, 350);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, focused, busy]);
  useEffect(() => {
    if (active >= 0) document.getElementById("suggestion-" + active)?.scrollIntoView?.({ block: "nearest" });
  }, [active]);
  useEffect(() => {
    if (results && !busy && !selected) {
      const target = document.getElementById("search-results");
      target?.focus({ preventScroll: true });
      target?.scrollIntoView?.({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
    }
  }, [results, busy, selected]);
  async function load(path: string, profile = false) {
    setFocused(false); setSuggestions([]); setSuggestionStatus("");
    setBusy(true); setError(""); setSelected(null); if (!profile) setResults(null);
    try {
      if (profile) setSelected(await request<DashboardData>(path));
      else {
        const data = await request<SearchResult>(path);
        setResults(data.items); setSources(data.sources);
      }
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  function choose(person: Politician, fromSuggestions = false) { if (fromSuggestions) setResults(suggestions); setQuery(person.name); void load("/politicians/" + person.provider + "/" + person.id + "/dashboard", true); }
  function navigate(section: "consulta" | "fontes") {
    if (section !== "fontes") setSelected(null);
    requestAnimationFrame(() => {
      const target = document.getElementById(section === "consulta" ? "public-search" : "fontes");
      target?.scrollIntoView?.({ block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
      if (section === "consulta") target?.focus({ preventScroll: true });
    });
  }
  const expanded = focused && !busy && suggestions.length > 0;
  return <><Header onNavigate={navigate} /><main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <section className="hero-outdoor" aria-label="Apresentação"><div className="hero-content">

<p className="mb-3 text-xs font-bold uppercase tracking-widest text-emerald-800">Dados oficiais · Três poderes</p>
    <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">Saiba todos os passos do seu candidato.</h1>
    <p className="mt-5 mb-8 max-w-3xl text-lg leading-relaxed text-slate-600">Encontre representantes e autoridades. Leia perfis, acompanhe os dados disponíveis e baixe relatórios sem sair daqui.</p>

    <form className="search-panel relative rounded-2xl border bg-white p-5 sm:p-6" onSubmit={event => { event.preventDefault(); void load("/search/all?q=" + encodeURIComponent(query.trim())); }}>
      <div className="search-fields flex flex-col gap-3"><div className="relative min-w-0 w-full"><label htmlFor="public-search" className="text-sm font-semibold">Nome da pessoa</label><input id="public-search" role="combobox" aria-autocomplete="list" aria-expanded={expanded} aria-controls={expanded ? "name-suggestions" : undefined} aria-activedescendant={expanded && active >= 0 ? "suggestion-" + active : undefined} autoComplete="off" className="mt-2 block w-full rounded-xl border bg-slate-50 p-4 font-normal" value={query} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onChange={event => { setQuery(event.target.value); setSources([]); setFocused(true); setSuggestions([]); setActive(-1); setSuggestionStatus(""); }} onKeyDown={event => {
        if (event.key === "Escape") { setFocused(false); setActive(-1); }
        if (expanded && (event.key === "ArrowDown" || event.key === "ArrowUp")) { event.preventDefault(); setActive(index => event.key === "ArrowDown" ? (index + 1) % suggestions.length : (index <= 0 ? suggestions.length - 1 : index - 1)); }
        if (expanded && event.key === "Enter" && active >= 0) { event.preventDefault(); choose(suggestions[active], true); }
      }} placeholder="Nome do candidato ou da autoridade" minLength={2} maxLength={100} required disabled={busy} />
      {expanded && <ul id="name-suggestions" role="listbox" aria-label="Sugestões de nomes" className="suggestions relative z-20 mt-2 max-h-80 w-full overflow-auto rounded-xl border bg-white p-2 shadow-2xl">{suggestions.map((person, index) => <li id={"suggestion-" + index} role="option" aria-selected={active === index} key={person.provider + "-" + person.id} className={"suggestion flex cursor-pointer items-center gap-3 rounded-lg p-3 " + (active === index ? "suggestion-active" : "")} onMouseDown={event => event.preventDefault()} onClick={() => choose(person, true)}><Portrait person={person} /><div className="min-w-0"><p className="font-semibold">{person.name}</p><p className="text-xs text-slate-500">{identity(person)}</p></div></li>)}</ul>}
      </div><button onMouseDown={event => { if (expanded) event.preventDefault(); }} className="w-full rounded-xl bg-emerald-900 px-8 py-4 font-semibold text-white" disabled={busy || query.trim().length < 2}>Buscar</button></div>
      {focused && suggestionStatus && <p role="status" className="mt-3 text-sm text-slate-500">{suggestionStatus}</p>}
      <p className="mt-3 text-xs text-slate-500">Digite ao menos 2 letras. Use ↑ ↓ e Enter para escolher uma sugestão.</p>
    </form>
    {sources.length > 0 && <details className="mt-4 text-xs leading-relaxed text-slate-500"><summary>{sources.some(source => !source.available) ? "Consulta parcial — algumas fontes indisponíveis" : "Fontes consultadas"}</summary><ul className="mt-2 space-y-1">{sources.map(source => <li key={source.provider}>{source.name}: {source.available ? `${source.matches} registro(s) encontrado(s)` : "indisponível nesta consulta"}</li>)}</ul></details>}
    {busy && <p role="status" className="mt-6">Consultando dados oficiais…</p>}
    {error && <p role="alert" className="mt-6 text-red-700">{error}</p>}

    </div><div className="hero-visual"><Image className="hero-art" src="/capivara-tres-poderes-v2.png" width={1536} height={1024} alt="Ilustração flat da capivara olhando por binóculos na Praça dos Três Poderes, com o Congresso, o Planalto e o STF ao fundo" unoptimized preload /><svg className="hero-stars" viewBox="0 0 500 100" aria-hidden="true">{[[22,18],[79,47],[142,12],[201,63],[268,29],[327,76],[389,16],[457,57],[49,83],[114,27],[183,91],[244,43],[305,9],[373,54],[432,86],[481,22],[17,59],[91,8],[157,69],[221,19],[287,88],[349,36],[411,70],[465,94],[58,39],[337,98]].map(([x, y], index) => <path key={index} transform={`translate(${x} ${y})`} d="M0-4 1-1 4 0 1 1 0 4-1 1-4 0-1-1Z" />)}</svg></div></section>
    {!selected && results && <section id="search-results" tabIndex={-1} className="mt-6" aria-label="Resultados"><h2 className="mb-4 text-xl font-bold">{results.length} resultado(s)</h2>
      {results.length === 0 && <p>Nenhuma pessoa encontrada nas fontes disponíveis. Isso não significa ausência de candidatura ou cargo.</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{results.map(person => <article className="rounded-2xl border bg-white p-6" key={person.provider + "-" + person.id}><p className="mb-3 text-xs uppercase tracking-widest text-slate-500">{identity(person)}</p><div className="flex items-center gap-3"><Portrait person={person} /><h3 className="text-xl font-bold">{person.name}</h3></div><p className="mt-3 text-sm text-slate-500">{person.institution || "Câmara dos Deputados"}</p><p className="my-3 text-slate-600">{person.party} · {person.state}</p><button className="mt-3 font-bold text-emerald-800" disabled={busy} onClick={() => choose(person)}>Puxar a capivara de {person.name}</button></article>)}</div>
    </section>}
    {selected && <Dashboard key={selected.politician.provider + selected.politician.id} data={selected} onBack={() => setSelected(null)} />}
    <Newsletter />
    <footer id="fontes" tabIndex={-1} className="mt-16 border-t pt-6 text-sm leading-relaxed text-slate-500">Fontes: Câmara, Senado, ministérios, STJ, cadastro oficial de governadores e candidaturas TSE 2026 e 2024. A busca consulta todas as integrações; fontes indisponíveis são identificadas. Registros eleitorais históricos não comprovam cargo ou filiação atuais. Não há cobertura de todos os bancos de dados públicos. Nenhuma pesquisa é salva pelo projeto.</footer>
  </main></>;
}
