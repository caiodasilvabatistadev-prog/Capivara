"use client";
import { useEffect, useState } from "react";
import { request, type Politician } from "../lib/api";

type NewsResult = { subject_name: string; fetched_at: string; notice: string; items: { title: string; publisher: string; published_at: string; source_url: string; reference_url: string; matched_terms: string[] }[] };
export default function News({ person }: { person: Politician }) {
  const [data, setData] = useState<NewsResult | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    request<NewsResult>(`/politicians/${person.provider}/${person.id}/news`)
      .then(result => { if (active) setData(result); })
      .catch(() => { if (active) setError("A busca de notícias está indisponível. Tente novamente."); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [person.provider, person.id, attempt]);
  return <section aria-label="Busca automática de notícias" className="mb-10 rounded-2xl border bg-white p-6">
    <p className="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-800">Busca automática · Sem revisão judicial</p>
    <h3 className="text-2xl font-bold">Notícias encontradas pelo nome</h3>
    <p className="my-4 text-sm leading-relaxed text-slate-600">Títulos com termos como condenado, suspeito, julgado, investigado, apologia e crime. A menção pode tratar de terceiros; não constitui acusação nem confirmação de culpa.</p>
    <p className="mb-4 text-xs text-slate-500">Veículos: G1, Folha, Estadão, UOL, CNN Brasil, Poder360 e Intercept Brasil.</p>
    {busy && <p role="status">Buscando notícias…</p>}
    {error && <p role="alert" className="mb-4 text-red-700">{error}</p>}
    {!busy && <button className="rounded-xl border px-4 py-3 text-sm font-semibold" onClick={() => { setBusy(true); setError(""); setData(null); setAttempt(value => value + 1); }}>Buscar novamente</button>}
    {data && Array.isArray(data.items) && <div className="mt-6"><p className="text-sm leading-relaxed text-slate-500">{data.notice}</p><p className="mt-2 text-xs text-slate-500">Consulta: {new Date(data.fetched_at).toLocaleString("pt-BR")} · Até 20 resultados · Data da reportagem não é data de decisão judicial.</p>
      {!data.items.length && <p className="mt-5">Nenhum título encontrado com os filtros nesta consulta.</p>}
      <div className="mt-5 space-y-4">{data.items.map(item => <article key={item.reference_url} className="rounded-xl border p-5"><p className="mb-2 text-xs text-slate-500">{item.publisher} · {new Date(item.published_at).toLocaleDateString("pt-BR")}</p><h4 className="font-bold">{item.title}</h4><p className="mt-3 text-xs text-slate-500">Termos encontrados no título: {item.matched_terms.join(", ")}. Situação judicial não verificada.</p><details className="mt-4 text-xs"><summary className="cursor-pointer font-semibold">Fonte e referência</summary><p className="mt-2 break-all">Veículo: {item.source_url}</p><p className="mt-2 break-all">Referência no Google Notícias: {item.reference_url}</p></details></article>)}</div>
    </div>}
  </section>;
}
