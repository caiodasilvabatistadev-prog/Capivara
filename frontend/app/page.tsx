"use client";
import { useEffect, useState } from "react";
import Dashboard from "../components/Dashboard";
import Portrait from "../components/Portrait";
import { type Politician, type DashboardData, request } from "../lib/api";

const coverage = {
  legislativo: "Deputados federais (Câmara) ou senadores em exercício (Senado).",
  executivo: "Cobertura inicial: titulares dos Ministérios da Saúde e da Fazenda. Perfis e contatos oficiais.",
  judiciario: "Cobertura inicial: ministros em atividade do STJ. Perfis e currículos oficiais.",
};
type Power = keyof typeof coverage;
export default function Home() {
  const [power, setPower] = useState<Power>("legislativo");
  const [house, setHouse] = useState("camara");
  const provider = power === "legislativo" ? house : power;
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Politician[] | null>(null);
  const [selected, setSelected] = useState<DashboardData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState<Politician[]>([]);
  const [focused, setFocused] = useState(false);
  const [active, setActive] = useState(-1);
  const [suggestionStatus, setSuggestionStatus] = useState("");
  const filter = provider === "camara" ? "" : "&provider=" + provider;
  useEffect(() => {
    if (!focused || busy || query.trim().length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSuggestionStatus("Buscando sugestões…");
      try {
        const people = await request<Politician[]>("/autocomplete?q=" + encodeURIComponent(query.trim()) + filter, controller.signal);
        if (!controller.signal.aborted) {
          setSuggestions(people); setActive(-1);
          setSuggestionStatus(people.length ? "" : "Nenhuma sugestão encontrada. Você pode tentar outra busca.");
        }
      } catch {
        if (!controller.signal.aborted) setSuggestionStatus("Sugestões indisponíveis. Tente o botão Buscar.");
      }
    }, 350);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, filter, focused, busy]);
  useEffect(() => {
    if (active >= 0) document.getElementById("suggestion-" + active)?.scrollIntoView?.({ block: "nearest" });
  }, [active]);
  async function load(path: string, profile = false) {
    setFocused(false); setSuggestions([]); setSuggestionStatus("");
    setBusy(true); setError(""); setSelected(null);
    try {
      if (profile) setSelected(await request<DashboardData>(path));
      else setResults(await request<Politician[]>(path));
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  function resetScope() { setResults(null); setSelected(null); setSuggestions([]); setSuggestionStatus(""); setActive(-1); setError(""); }
  function choose(person: Politician, fromSuggestions = false) { if (fromSuggestions) setResults(suggestions); setQuery(person.name); void load("/politicians/" + person.provider + "/" + person.id + "/dashboard", true); }
  const expanded = focused && !busy && suggestions.length > 0;
  return <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <div className="mb-10 flex items-center justify-between gap-3"><div className="flex items-center gap-3"><span aria-hidden="true" className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-900 font-bold text-white">C</span><div><p className="font-bold">Capivara</p><p className="text-xs text-slate-500">Transparência para acompanhar o poder público</p></div></div><span className="rounded-full border px-3 py-2 text-xs text-slate-500">Consulta federal</span></div>
    <p className="mb-3 text-xs font-bold uppercase tracking-widest text-emerald-800">Dados oficiais · Três poderes</p>
    <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">O poder público, mais perto de você.</h1>
    <p className="mt-5 mb-8 max-w-3xl text-lg leading-relaxed text-slate-600">Encontre representantes e autoridades. Leia perfis, acompanhe os dados disponíveis e baixe relatórios sem sair daqui.</p>
    <div role="group" aria-label="Poder consultado" className="mb-5 flex flex-wrap gap-3">{(["legislativo", "executivo", "judiciario"] as Power[]).map(value => <button key={value} disabled={busy} aria-pressed={power === value} className={"scope rounded-xl border px-5 py-3 font-semibold " + (power === value ? "scope-selected" : "")} onClick={() => { setPower(value); resetScope(); }}>{value === "judiciario" ? "Judiciário" : value[0].toUpperCase() + value.slice(1)}</button>)}</div>
    <form className="search-panel relative rounded-2xl border bg-white p-5 sm:p-6" onSubmit={event => { event.preventDefault(); void load("/search?q=" + encodeURIComponent(query.trim()) + filter); }}>
      <div className="mb-5 flex flex-wrap items-center gap-3">{power === "legislativo" && <label className="text-sm font-semibold">Casa legislativa<select className="ml-3 rounded-lg border bg-slate-50 px-3 py-2" value={house} disabled={busy} onChange={event => { setHouse(event.target.value); resetScope(); }}><option value="camara">Câmara dos Deputados</option><option value="senado">Senado Federal</option></select></label>}<p className="text-sm leading-relaxed text-slate-500">{coverage[power]}</p></div>
      <div className="flex flex-wrap gap-3"><div className="relative min-w-0 flex-1 basis-64"><label htmlFor="public-search" className="text-sm font-semibold">Nome da pessoa</label><input id="public-search" role="combobox" aria-autocomplete="list" aria-expanded={expanded} aria-controls={expanded ? "name-suggestions" : undefined} aria-activedescendant={expanded && active >= 0 ? "suggestion-" + active : undefined} autoComplete="off" className="mt-2 block w-full rounded-xl border bg-slate-50 p-4 font-normal" value={query} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onChange={event => { setQuery(event.target.value); setFocused(true); setSuggestions([]); setActive(-1); setSuggestionStatus(""); }} onKeyDown={event => {
        if (event.key === "Escape") { setFocused(false); setActive(-1); }
        if (expanded && (event.key === "ArrowDown" || event.key === "ArrowUp")) { event.preventDefault(); setActive(index => event.key === "ArrowDown" ? (index + 1) % suggestions.length : (index <= 0 ? suggestions.length - 1 : index - 1)); }
        if (expanded && event.key === "Enter" && active >= 0) { event.preventDefault(); choose(suggestions[active], true); }
      }} placeholder={power === "executivo" ? "Ex.: Padilha" : power === "judiciario" ? "Ex.: Antonio Carlos" : "Ex.: André Fernandes"} minLength={2} maxLength={100} required disabled={busy} />
      {expanded && <ul id="name-suggestions" role="listbox" aria-label="Sugestões de nomes" className="suggestions absolute z-20 mt-2 max-h-80 w-full overflow-auto rounded-xl border bg-white p-2 shadow-2xl">{suggestions.map((person, index) => <li id={"suggestion-" + index} role="option" aria-selected={active === index} key={person.provider + "-" + person.id} className={"suggestion flex cursor-pointer items-center gap-3 rounded-lg p-3 " + (active === index ? "suggestion-active" : "")} onMouseDown={event => event.preventDefault()} onClick={() => choose(person, true)}><Portrait person={person} /><div className="min-w-0"><p className="font-semibold">{person.name}</p><p className="text-xs text-slate-500">{person.role || "Deputado federal"} · {person.institution || "Câmara dos Deputados"}</p></div></li>)}</ul>}
      </div><button className="self-end rounded-xl bg-emerald-900 px-8 py-4 font-semibold text-white" disabled={busy || query.trim().length < 2}>Buscar</button></div>
      {focused && suggestionStatus && <p role="status" className="mt-3 text-sm text-slate-500">{suggestionStatus}</p>}
      <p className="mt-3 text-xs text-slate-500">Digite ao menos 2 letras. Use ↑ ↓ e Enter para escolher uma sugestão.</p>
    </form>
    {busy && <p role="status" className="mt-6">Consultando dados oficiais…</p>}
    {error && <p role="alert" className="mt-6 text-red-700">{error}</p>}
    {!selected && results && <section className="mt-10" aria-label="Resultados"><h2 className="mb-4 text-xl font-bold">{results.length} resultado(s)</h2>
      {results.length === 0 && <p>Nenhuma pessoa encontrada nesta fonte.</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{results.map(person => <article className="rounded-2xl border bg-white p-6" key={person.provider + "-" + person.id}><p className="mb-3 text-xs uppercase tracking-widest text-slate-500">{person.role || "Deputado federal"}</p><div className="flex items-center gap-3"><Portrait person={person} /><h3 className="text-xl font-bold">{person.name}</h3></div><p className="mt-3 text-sm text-slate-500">{person.institution || "Câmara dos Deputados"}</p><p className="my-3 text-slate-600">{person.party} · {person.state}</p><button className="mt-3 font-bold text-emerald-800" disabled={busy} onClick={() => choose(person)}>Ver dashboard de {person.name}</button></article>)}</div>
    </section>}
    {selected && <Dashboard data={selected} onBack={() => setSelected(null)} />}
    <footer className="mt-16 border-t pt-6 text-sm leading-relaxed text-slate-500">Fontes: Câmara, Senado, Ministérios da Saúde e da Fazenda e STJ. Cobertura federal inicial, sem cadastro completo de autoridades ou confirmação de candidaturas. Nenhuma pesquisa é salva pelo projeto.</footer>
  </main>;
}
