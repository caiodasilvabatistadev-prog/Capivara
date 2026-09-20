"use client";
import { useEffect, useState } from "react";
import { request, type Politician } from "../lib/api";
import Portrait from "./Portrait";

type BiographyData = {
  found: boolean;
  title: string;
  description: string;
  extract: string;
  source_url: string;
  fetched_at: string;
  notice: string;
  media: { title: string; publisher: string; published_at: string; source_url: string; reference_url: string }[];
};

export default function Biography({ person }: { person: Politician }) {
  const [data, setData] = useState<BiographyData | null>(null);
  const [error, setError] = useState("");
  const media = data?.media ?? [];
  useEffect(() => {
    const controller = new AbortController();
    request<BiographyData>(`/politicians/${person.provider}/${person.id}/biography`, controller.signal)
      .then(setData)
      .catch(value => { if (value?.name !== "AbortError") setError("A biografia complementar está indisponível nesta consulta."); });
    return () => controller.abort();
  }, [person.id, person.provider]);
  return <section aria-label="Breve biografia" className="mb-10 rounded-2xl border bg-white p-6">
    <div className="flex items-start gap-4"><Portrait person={person} /><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Conheça a trajetória</p><h3 className="mt-1 text-2xl font-bold">Breve biografia de {person.name}</h3></div></div>
    {!data && !error && <p role="status" className="mt-4 text-sm text-slate-500">Consultando a Wikipédia em português…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-slate-500">{error}</p>}
    {data && !data.found && <p className="mt-4 text-sm text-slate-500">Não encontramos um artigo com título exatamente igual ao nome oficial. Isso evita atribuir a biografia de um homônimo.</p>}
    {data?.found && <><p className="mt-4 text-sm font-semibold text-slate-300">{data.description}</p><p className="mt-3 leading-relaxed text-slate-100">{data.extract}</p><p className="mt-4 rounded-xl bg-amber-50 p-3 text-xs leading-relaxed text-amber-950">{data.notice}</p><details className="mt-3 text-xs text-slate-500"><summary className="cursor-pointer font-semibold">Fonte complementar</summary><p className="mt-2 break-all">{data.source_url}</p><p className="mt-1">Consulta: {new Date(data.fetched_at).toLocaleString("pt-BR")}</p></details></>}
    {data && <div className="mt-6 border-t pt-5"><h4 className="font-bold">Contexto publicado pela imprensa</h4><p className="mt-2 text-xs leading-relaxed text-slate-400">Seleção automática de matérias que citam o nome completo. Títulos jornalísticos são apresentados como contexto e não como comprovação isolada.</p>{media.length ? <ul className="mt-4 space-y-3">{media.map(item => <li className="rounded-xl bg-slate-50 p-4" key={item.reference_url}><p className="font-semibold leading-relaxed text-slate-100">{item.title}</p><p className="mt-2 text-xs text-slate-400">{item.publisher} · {new Date(item.published_at).toLocaleDateString("pt-BR")}</p></li>)}</ul> : <p className="mt-4 text-sm text-slate-400">Nenhuma matéria dos veículos selecionados foi localizada nesta consulta.</p>}</div>}
  </section>;
}
