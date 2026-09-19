"use client";
import { useEffect, useState } from "react";
import { request, type Politician } from "../lib/api";
import Portrait from "./Portrait";

type Item = { title: string; detail: string; period: string };
type CareerData = { available: boolean; professions: Item[]; previous_offices: Item[]; notice: string };
type Matches = { profession: string; people: Politician[]; notice: string };

export default function Career({ person }: { person: Politician }) {
  const [data, setData] = useState<CareerData | null>(null);
  const [error, setError] = useState("");
  const [matches, setMatches] = useState<Matches | null>(null);
  const [matching, setMatching] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    request<CareerData>(`/politicians/${person.provider}/${person.id}/career`, controller.signal).then(setData).catch(value => { if (value?.name !== "AbortError") setError("A trajetória profissional está indisponível nesta consulta."); });
    return () => controller.abort();
  }, [person.id, person.provider]);
  return <section aria-label="Trajetória profissional" className="mb-10 rounded-2xl border bg-white p-6">
    <div className="flex items-center gap-4"><Portrait person={person} /><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Antes e durante a política</p><h3 className="text-2xl font-bold">Profissão e cargos anteriores</h3></div></div>
    {!data && !error && <p role="status" className="mt-4 text-sm text-slate-500">Consultando a trajetória oficial…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-slate-500">{error}</p>}
    {data && !data.available && <p className="mt-4 text-sm text-slate-600">{data.notice}</p>}
    {data?.available && <><div className="mt-5 grid gap-5 md:grid-cols-2"><div><h4 className="font-bold">Profissões declaradas</h4>{data.professions.length ? <ul className="mt-3 flex flex-wrap gap-2">{data.professions.map(item => <li key={item.title}><button className="rounded-full border border-emerald-700 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-950" onClick={async () => { setMatching(item.title); setMatches(null); try { setMatches(await request<Matches>(`/professions?name=${encodeURIComponent(item.title)}`)); } finally { setMatching(""); } }}>{matching === item.title ? "Consultando…" : item.title}</button></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">Nenhuma profissão publicada.</p>}</div><div><h4 className="font-bold">Mandatos fora da Câmara</h4>{data.previous_offices.length ? <ul className="mt-3 space-y-2">{data.previous_offices.map(item => <li className="rounded-xl bg-slate-50 p-3" key={`${item.title}-${item.period}`}><strong>{item.title}</strong><p className="text-sm text-slate-600">{item.detail || "Local e partido não informados"} · {item.period}</p></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">Nenhum mandato anterior publicado.</p>}</div></div>{matches && <div className="mt-6 rounded-xl border p-4"><h4 className="font-bold">Deputados em exercício: {matches.profession}</h4><p className="mt-1 text-xs text-slate-500">{matches.notice}</p><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{matches.people.map(candidate => <a className="flex items-center gap-3 rounded-xl bg-slate-50 p-3" href={`/?provider=${candidate.provider}&id=${candidate.id}#public-search`} key={candidate.id}><Portrait person={candidate} /><span><strong className="block">{candidate.name}</strong><small>{candidate.role} · {candidate.party}-{candidate.state}</small></span></a>)}</div></div>}<p className="mt-5 text-xs text-slate-500">{data.notice}</p></>}
  </section>;
}
