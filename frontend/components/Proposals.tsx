"use client";

import { useEffect, useState } from "react";
import { request, type DashboardData, type Politician } from "../lib/api";

type Section = DashboardData["sections"][number];

export default function Proposals({ person, initialYear, onLoaded }: { person: Politician; initialYear?: string | null; onLoaded: (section: Section) => void }) {
  const current = new Date().getUTCFullYear();
  const parsed = Number(initialYear);
  const [year, setYear] = useState(Number.isInteger(parsed) && parsed >= 2000 && parsed <= current ? parsed : current);
  const [data, setData] = useState<Section | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<"authored" | "reported">("authored");
  async function load(selectedKind: "authored" | "reported" = kind) {
    setKind(selectedKind);
    setBusy(true); setError("");
    try {
      const result = await request<Section>(`/politicians/${person.provider}/${person.id}/proposals?year=${year}&kind=${selectedKind}`);
      setData(result); onLoaded(result);
    } catch { setError("Não foi possível consultar as propostas agora. Tente novamente."); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    const open = (event: Event) => void load((event as CustomEvent<"authored" | "reported">).detail);
    window.addEventListener("open-proposals", open);
    return () => window.removeEventListener("open-proposals", open);
  });
  if (person.provider !== "camara") return null;
  const table = data?.blocks.find(block => block.kind === "table");
  const rows = (table?.rows.slice(1) || []).filter(row => row.slice(1, 5).join(" ").toLocaleLowerCase("pt-BR").includes(query.toLocaleLowerCase("pt-BR")));
  return <section id="propostas-detalhadas" className="mb-10 scroll-mt-32 rounded-2xl border bg-white p-6" aria-label="Lista de propostas de sua autoria">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Feitos registrados pela Câmara</p>
    <h3 className="mt-2 text-2xl font-bold">Propostas de autoria e relatadas, em linguagem simples</h3>
    <p className="mt-3 text-sm leading-relaxed text-slate-600">Autoria indica quem assinou a proposta. Relatoria indica quem analisou uma proposta e apresentou parecer. Veja a descrição original e a fonte oficial em cada item.</p>
    <div className="mt-5 flex flex-wrap items-end gap-3">
      <div className="flex gap-2" aria-label="Tipo de participação"><button className={`rounded-lg border px-3 py-2 text-sm font-semibold ${kind === "authored" ? "bg-emerald-900 text-white" : ""}`} aria-pressed={kind === "authored"} onClick={() => { setKind("authored"); setData(null); }}>De sua autoria</button><button className={`rounded-lg border px-3 py-2 text-sm font-semibold ${kind === "reported" ? "bg-emerald-900 text-white" : ""}`} aria-pressed={kind === "reported"} onClick={() => { setKind("reported"); setData(null); }}>Relatadas por esta pessoa</button></div>
      <label className="text-sm font-semibold">Ano<select className="ml-3 rounded-lg border bg-slate-50 p-2 font-normal" value={year} disabled={busy} onChange={event => { setYear(Number(event.target.value)); setData(null); }} aria-label="Ano das propostas">{Array.from({ length: current - 1999 }, (_, index) => current - index).map(value => <option key={value}>{value}</option>)}</select></label>
      <button className="rounded-xl border px-4 py-3 text-sm font-semibold" disabled={busy} onClick={() => void load()}>{busy ? "Consultando propostas…" : kind === "authored" ? "Listar propostas de autoria" : "Listar propostas relatadas"}</button>
    </div>
    {error && <p className="mt-4 text-red-700" role="alert">{error}</p>}
    {data && <div className="mt-6">
      {data.blocks.filter(block => block.kind === "text").map(block => <p className="mb-2 text-xs leading-relaxed text-slate-500" key={block.text}>{block.text}</p>)}
      <label className="mt-5 block text-sm font-semibold">Buscar nesta lista<input className="mt-2 block w-full rounded-xl border bg-slate-50 p-3 font-normal" value={query} onChange={event => setQuery(event.target.value)} placeholder="Ex.: saúde, escola ou imposto" /></label>
      <p className="my-4 text-xs text-slate-500">{rows.length} proposta(s) exibida(s).</p>
      {!rows.length && <p className="text-sm text-slate-600">Nenhuma proposta encontrada neste recorte.</p>}
      <div className="grid gap-4 lg:grid-cols-2">{rows.map(row => <article className="rounded-xl border p-5" key={`${row[1]}-${row[0]}`}>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span>{row[1]}</span><span>{row[0].split("-").reverse().join("/")}</span></div>
        <h4 className="mt-3 text-lg font-bold leading-snug">{row[2]}</h4>
        <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm font-semibold text-emerald-950">Situação: {row[4]}</p>
        <details className="mt-4 text-sm"><summary className="cursor-pointer font-semibold">Ler descrição original</summary><p className="mt-2 leading-relaxed text-slate-600">{row[3]}</p></details>
        <a className="mt-4 inline-block text-sm font-bold text-emerald-800 underline" href={row[5]} target="_blank" rel="noreferrer">Conferir na Câmara</a>
      </article>)}</div>
    </div>}
  </section>;
}
