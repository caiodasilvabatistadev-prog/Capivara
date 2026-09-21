"use client";
import { useEffect, useState } from "react";
import { request, type Politician } from "../lib/api";
import Portrait from "./Portrait";

type Member = { name: string; relationship: string; description: string; evidence_url: string; political_profile?: boolean };
type FamilyData = { found: boolean; members: Member[]; source_url: string; fetched_at: string; notice: string };

export default function PoliticalFamily({ person }: { person: Politician }) {
  const [data, setData] = useState<FamilyData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    request<FamilyData>(`/politicians/${person.provider}/${person.id}/family`, controller.signal)
      .then(setData)
      .catch(value => { if (value?.name !== "AbortError") setError("Os vínculos familiares documentados estão indisponíveis nesta consulta."); });
    return () => controller.abort();
  }, [person.id, person.provider]);
  return <section aria-label="Parentescos documentados" className="mb-10 rounded-2xl border bg-white p-6">
    <div className="flex items-center gap-4"><Portrait person={person} /><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Família e política</p><h3 className="text-2xl font-bold">Parentescos documentados</h3></div></div>
    {!data && !error && <p role="status" className="mt-4 text-sm text-slate-500">Conferindo vínculos com referência…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-slate-500">{error}</p>}
    {data && !data.found && <p className="mt-4 text-sm text-slate-600">Nenhum parentesco com referência foi encontrado na fonte integrada. Isso não comprova ausência de parentes políticos.</p>}
    {data?.found && <div className="family-tree mt-6"><div className="family-root mx-auto flex w-fit max-w-full items-center gap-3 rounded-2xl border-2 border-emerald-700 bg-emerald-50 p-4"><Portrait person={person} /><div><p className="text-xs font-bold uppercase tracking-wide text-emerald-800">Pessoa consultada</p><p className="font-bold">{person.name}</p><p className="text-xs text-slate-600">{person.role || "Cargo público"} · {person.party}</p></div></div><div className="family-branches grid gap-4 pt-10 sm:grid-cols-2">{data.members.map(member => <article className="family-member rounded-xl border bg-slate-50 p-4" key={`${member.relationship}-${member.name}`}><p className="text-xs font-bold uppercase tracking-wide text-emerald-800">{member.relationship}</p><p className="mt-1 font-bold">{member.name}</p>{member.description && <p className="mt-1 text-sm text-slate-600">{member.description}</p>}<div className="mt-3 flex flex-wrap gap-4">{member.political_profile && <a className="text-sm font-bold text-emerald-800 underline" href={`/?q=${encodeURIComponent(member.name)}#public-search`}>Puxar a capivara de {member.name}</a>}<a className="text-sm font-semibold text-emerald-800 underline" href={member.evidence_url} target="_blank" rel="noreferrer">Ver documento do parentesco</a></div></article>)}</div></div>}
    {data && <p className="mt-5 rounded-xl bg-amber-50 p-3 text-xs leading-relaxed text-amber-950">{data.notice}</p>}
  </section>;
}
