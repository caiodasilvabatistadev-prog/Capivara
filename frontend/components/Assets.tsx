"use client";
import { useEffect, useState } from "react";
import { request, type Politician } from "../lib/api";
import Portrait from "./Portrait";

type Asset = { kind: string; description: string; value: string; company_url?: string | null };
type Data = { available: boolean; election_year?: number | null; total: string; assets: Asset[]; source_url: string; notice: string };
const brl = (value: string) => Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function Assets({ person }: { person: Politician }) {
  const [data, setData] = useState<Data | null>(null); const [error, setError] = useState("");
  useEffect(() => { const controller = new AbortController(); request<Data>(`/politicians/${person.provider}/${person.id}/assets`, controller.signal).then(setData).catch(value => { if (value?.name !== "AbortError") setError("Os bens declarados estão indisponíveis nesta consulta."); }); return () => controller.abort(); }, [person.id, person.provider]);
  return <section className="mb-10 rounded-2xl border bg-white p-6" aria-label="Bens declarados">
    <div className="flex items-center gap-4"><Portrait person={person} /><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Declaração eleitoral</p><h3 className="text-2xl font-bold">Bens declarados por {person.name}</h3></div></div>
    {!data && !error && <p role="status" className="mt-4 text-sm text-slate-500">Consultando a declaração no TSE…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-slate-500">{error}</p>}
    {data && <><p className="mt-5 text-sm leading-relaxed text-slate-600">{data.notice}</p>{data.available ? <><p className="mt-5 text-lg font-bold">Total declarado na candidatura de {data.election_year}: {brl(data.total)}</p>{data.assets.length ? <div className="mt-4 grid gap-3 md:grid-cols-2">{data.assets.map((item, index) => <article className="rounded-xl bg-slate-50 p-4" key={`${item.kind}-${index}`}><p className="text-xs font-bold uppercase tracking-wide text-emerald-800">{item.kind}</p><p className="mt-2 text-sm leading-relaxed">{item.description}</p><p className="mt-3 font-bold">{brl(item.value)}</p>{item.company_url && <a href={item.company_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm font-bold text-emerald-800 underline">Site oficial da empresa</a>}</article>)}</div> : <p className="mt-4 text-sm">A candidatura foi encontrada, mas não há bens publicados nessa declaração.</p>}</> : <div className="mt-4 rounded-xl bg-amber-50 p-4 text-sm leading-relaxed text-amber-950"><strong>Por que pode não aparecer?</strong> A base é eleitoral, não um cadastro anual de patrimônio. O sistema procura uma candidatura de {data.election_year} pelo nome completo e estado. Pessoas nomeadas, quem não concorreu nesse ano ou nomes divergentes podem não ter correspondência segura.</div>}<a className="mt-5 inline-block text-sm font-bold text-emerald-800 underline" href={data.source_url} target="_blank" rel="noreferrer">Conferir a base oficial do TSE</a></>}
  </section>;
}
