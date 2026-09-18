"use client";
import { useState } from "react";

type Politician = { id: number; provider: string; name: string; party: string; state: string; email: string | null; source_url: string };
const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${api}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Não foi possível consultar os dados. Tente novamente.");
  return response.json();
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Politician[] | null>(null);
  const [selected, setSelected] = useState<Politician | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(path: string, profile = false) {
    setBusy(true); setError(""); setSelected(null);
    try {
      if (profile) setSelected(await request<Politician>(path));
      else setResults(await request<Politician[]>(path));
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-4xl px-6 py-14">
    <p className="mb-8 text-sm font-bold uppercase tracking-widest">Dados abertos · Câmara dos Deputados</p>
    <h1 className="text-5xl font-bold">Consulta Pública</h1>
    <p className="mt-5 mb-10 text-lg text-slate-600">Conheça quem representa você. Consulte informações oficiais de deputados federais por nome.</p>
    <form className="flex flex-wrap gap-3" onSubmit={event => { event.preventDefault(); void load(`/search?q=${encodeURIComponent(query.trim())}`); }}>
      <label className="flex-1">Nome do parlamentar<input className="mt-2 block w-full rounded-xl border bg-white p-4" value={query} onChange={event => setQuery(event.target.value)} placeholder="Digite pelo menos dois caracteres" minLength={2} maxLength={100} required /></label>
      <button className="self-end rounded-xl bg-emerald-900 px-8 py-4 text-white" disabled={busy || query.trim().length < 2}>Buscar</button>
    </form>
    {busy && <p role="status" className="mt-6">Consultando dados…</p>}
    {error && <p role="alert" className="mt-6 text-red-700">{error}</p>}
    {results && <section className="mt-10" aria-label="Resultados"><h2 className="mb-4 text-xl font-bold">{results.length} resultado(s)</h2>
      {results.length === 0 && <p>Nenhum parlamentar encontrado.</p>}
      <div className="grid gap-4 sm:grid-cols-2">{results.map(person => <article className="rounded-xl border bg-white p-6" key={person.id}><h3 className="text-xl font-bold">{person.name}</h3><p className="my-3">{person.party} · {person.state}</p><button className="font-bold text-emerald-800" disabled={busy} onClick={() => void load(`/politicians/${person.provider}/${person.id}`, true)}>Ver perfil de {person.name}</button></article>)}</div>
    </section>}
    {selected && <section aria-label="Perfil" className="mt-8 rounded-xl border bg-white p-8"><h2 className="text-2xl font-bold">{selected.name}</h2><p className="my-3">{selected.party} · {selected.state}</p><p>{selected.email || "E-mail não informado pela fonte"}</p><a className="mt-5 inline-block underline" href={selected.source_url} target="_blank" rel="noreferrer">Consultar fonte oficial</a><button className="ml-6 underline" onClick={() => window.print()}>Imprimir perfil</button></section>}
    <footer className="mt-16 border-t pt-6 text-sm text-slate-600">Fonte: Dados Abertos da Câmara dos Deputados. As informações refletem a resposta da fonte no momento da consulta.</footer>
  </main>;
}
