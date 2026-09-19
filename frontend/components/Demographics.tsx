"use client";
import { useEffect, useState } from "react";
import { request } from "../lib/api";

type Group = { label: string; value: number; percentage: number };
type Snapshot = { year: number; scope: string; total: number; sex_total: number; race_total: number; sex: Group[]; race: Group[]; source_url: string; notice: string };
const colors = ["#34d399", "#60a5fa", "#fbbf24", "#f472b6", "#a78bfa", "#fb7185", "#94a3b8"];

function Donut({ title, groups, total }: { title: string; groups: Group[]; total: number }) {
  const stops = groups.map((group, index) => {
    const start = groups.slice(0, index).reduce((sum, item) => sum + item.percentage, 0);
    return `${colors[index % colors.length]} ${start}% ${start + group.percentage}%`;
  }).join(", ");
  return <article className="rounded-2xl border bg-white p-6">
    <h3 className="text-xl font-bold">{title}</h3>
    <div className="mt-6 grid items-center gap-6 sm:grid-cols-[180px_1fr]">
      <div className="relative mx-auto h-44 w-44 rounded-full" role="img" aria-label={`${title}: ${groups.map(group => `${group.label} ${group.percentage}%`).join(", ")}`} style={{ background: `conic-gradient(${stops || "#cbd5e1 0 100%"})` }}><div className="absolute inset-8 flex flex-col items-center justify-center rounded-full bg-white text-center"><strong className="text-xl">{total.toLocaleString("pt-BR")}</strong><span className="text-xs text-slate-500">registros</span></div></div>
      <ul className="space-y-3">{groups.map((group, index) => <li className="grid grid-cols-[12px_1fr_auto] items-center gap-2 text-sm" key={group.label}><span className="h-3 w-3 rounded-full" style={{ background: colors[index % colors.length] }} /><span>{group.label}</span><strong>{group.percentage.toLocaleString("pt-BR")} %</strong><span className="col-start-2 text-xs text-slate-500">{group.value.toLocaleString("pt-BR")} candidaturas</span></li>)}</ul>
    </div>
  </article>;
}

export default function Demographics() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    request<Snapshot>("/demographics?year=2024", controller.signal).then(setData).catch(() => { if (!controller.signal.aborted) setError("Não foi possível consultar a base eleitoral agora."); });
    return () => controller.abort();
  }, []);
  return <section aria-label="Dados demográficos autodeclarados" className="mt-12">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Autodeclaração publicada pelo TSE</p><h2 className="mt-2 text-3xl font-bold">Sexo e raça/cor das candidaturas</h2></div><p className="rounded-xl border bg-white px-4 py-3 text-sm font-semibold">Ano eleitoral: 2024</p></div>
    <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600">Mostramos primeiro somente características declaradas pelos próprios candidatos. Não inferimos identidade por nome, fotografia ou reportagem.</p>
    {!data && !error && <p role="status" className="mt-6">Consultando a base eleitoral do TSE…</p>}
    {error && <p role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-800">{error}</p>}
    {data && <><div className="mt-6 rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-950"><strong>{data.scope} · Eleições {data.year}</strong><p className="mt-1">{data.notice}</p></div><div className="mt-6 grid gap-5 lg:grid-cols-2"><Donut title="Sexo autodeclarado" groups={data.sex} total={data.sex_total} /><Donut title="Raça/cor autodeclarada" groups={data.race} total={data.race_total} /></div><p className="mt-4 text-xs leading-relaxed text-slate-500">Fonte: <a className="font-semibold text-emerald-800 underline" href={data.source_url} target="_blank" rel="noreferrer">Publicação oficial do TSE — candidaturas {data.year}</a>. Próxima etapa: conciliar estes registros com a relação oficial de mandatos em exercício.</p></>}
    <p className="mt-4 rounded-xl bg-amber-50 p-4 text-xs leading-relaxed text-amber-950">Orientação sexual não aparece neste painel. As integrações atuais não oferecem cadastro oficial completo e consentido dessa informação.</p>
  </section>;
}
