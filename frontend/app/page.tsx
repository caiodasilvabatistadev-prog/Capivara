"use client";
import { useState } from "react";
import Dashboard from "../components/Dashboard";
import { type Politician, type DashboardData, request } from "../lib/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Politician[] | null>(null);
  const [selected, setSelected] = useState<DashboardData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(path: string, profile = false) {
    setBusy(true); setError(""); setSelected(null);
    try {
      if (profile) setSelected(await request<DashboardData>(path));
      else setResults(await request<Politician[]>(path));
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <div className="mb-10 flex items-center gap-3"><span aria-hidden="true" className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-900 font-bold text-white">C</span><div><p className="font-bold">Capivara</p><p className="text-xs text-slate-500">Transparência para acompanhar o mandato</p></div></div>
    <p className="mb-3 text-xs font-bold uppercase tracking-widest text-emerald-800">Dados públicos · Deputados federais</p>
    <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">Entenda o mandato de quem representa você.</h1>
    <p className="mt-5 mb-8 max-w-3xl text-lg leading-relaxed text-slate-600">Gastos, presença e atuação legislativa em uma leitura simples, com dados oficiais da Câmara dos Deputados.</p>
    <form className="flex flex-wrap gap-3 rounded-2xl border bg-white p-5 sm:p-6" onSubmit={event => { event.preventDefault(); void load(`/search?q=${encodeURIComponent(query.trim())}`); }}>
      <label className="flex-1 text-sm font-semibold">Nome do parlamentar<input className="mt-2 block w-full rounded-xl border bg-slate-50 p-4 font-normal" value={query} onChange={event => setQuery(event.target.value)} placeholder="Ex.: André Fernandes" minLength={2} maxLength={100} required /></label>
      <button className="self-end rounded-xl bg-emerald-900 px-8 py-4 font-semibold text-white" disabled={busy || query.trim().length < 2}>Buscar</button>
    </form>
    {busy && <p role="status" className="mt-6">Consultando dados oficiais…</p>}
    {error && <p role="alert" className="mt-6 text-red-700">{error}</p>}
    {!selected && results && <section className="mt-10" aria-label="Resultados"><h2 className="mb-4 text-xl font-bold">{results.length} resultado(s)</h2>
      {results.length === 0 && <p>Nenhum parlamentar encontrado.</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{results.map(person => <article className="rounded-2xl border bg-white p-6" key={person.id}><p className="mb-3 text-xs uppercase tracking-widest text-slate-500">Deputado federal</p><h3 className="text-xl font-bold">{person.name}</h3><p className="my-3 text-slate-600">{person.party} · {person.state}</p><button className="mt-3 font-bold text-emerald-800" disabled={busy} onClick={() => void load(`/politicians/${person.provider}/${person.id}/dashboard`, true)}>Ver dashboard de {person.name}</button></article>)}</div>
    </section>}
    {selected && <Dashboard data={selected} onBack={() => setSelected(null)} />}
    <footer className="mt-16 border-t pt-6 text-sm leading-relaxed text-slate-500">Fonte: Dados Abertos e Portal da Câmara dos Deputados. A consulta cobre deputados federais; não confirma candidaturas eleitorais. Nenhuma pesquisa é salva pelo projeto.</footer>
  </main>;
}
