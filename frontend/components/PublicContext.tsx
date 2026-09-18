"use client";
import { useState } from "react";
import { request, type Politician, type ReportBlock } from "../lib/api";

type Source = { publisher: string; url: string; published_at: string };
export type Context = {
  subject_name: string; reviewed_at: string | null; notice: string;
  actions: { title: string; summary: string; attribution: string; stage: "proposta" | "aprovada" | "executada"; stage_as_of: string; official_source: Source; journalism: Source }[];
  cases: { title: string; summary: string; category: string; status: keyof typeof statuses; court: string; case_number: string; status_as_of: string; final_judgment: boolean; official_source: Source; journalism: Source }[];
};
const statuses = {
  condenacao_definitiva: "Condenação definitiva — trânsito em julgado",
  condenacao_recorrivel: "Condenação com possibilidade de recurso — não definitiva",
  em_andamento: "Processo em andamento — sem condenação registrada nesta revisão",
  absolvido: "Absolvido neste processo", arquivado: "Processo arquivado",
  anulado: "Decisão anulada", pedido_rejeitado: "Pedido rejeitado / ação improcedente",
};
const stages = { proposta: "Proposta", aprovada: "Aprovada", executada: "Execução documentada" };
function formatted(value: string) { return value.split("-").reverse().join("/"); }
function sourceText(source: Source) { return source.publisher + " · " + formatted(source.published_at) + " · " + source.url; }
function Sources({ official, journalism }: { official: Source; journalism: Source }) {
  return <details className="mt-4 text-xs text-slate-500"><summary className="cursor-pointer font-semibold">Fontes e datas</summary><p className="mt-3 break-all leading-relaxed">Fonte oficial: {sourceText(official)}</p><p className="mt-2 break-all leading-relaxed">Jornalismo: {sourceText(journalism)}</p></details>;
}
export function contextBlocks(data: Context): ReportBlock[] {
  const text = (value: string): ReportBlock => ({ kind: "text", text: value, rows: [] });
  return [text(data.notice), text("Revisão editorial: " + (data.reviewed_at ? formatted(data.reviewed_at) : "Não realizada")),
    ...data.actions.flatMap(item => [text(item.title + " | " + stages[item.stage] + " em " + formatted(item.stage_as_of)), text(item.summary), text(item.attribution), text("Fonte oficial: " + sourceText(item.official_source)), text("Jornalismo: " + sourceText(item.journalism))]),
    ...data.cases.flatMap(item => [text(item.title + " | " + statuses[item.status]), text(item.summary), text("Natureza: " + item.category + " | " + item.court + " | " + item.case_number), text("Estado na data: " + formatted(item.status_as_of)), text("Fonte judicial: " + sourceText(item.official_source)), text("Jornalismo: " + sourceText(item.journalism))]),
  ];
}
export default function PublicContext({ person, onLoaded }: { person: Politician; onLoaded: (value: Context) => void }) {
  const [data, setData] = useState<Context | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load() {
    setBusy(true); setError("");
    try { const result = await request<Context>("/politicians/" + person.provider + "/" + person.id + "/context"); setData(result); onLoaded(result); }
    catch { setError("Não foi possível consultar os registros revisados. Tente novamente."); }
    finally { setBusy(false); }
  }
  return <section id="public-context" aria-label="Notícias e situação judicial" className="mb-10 rounded-2xl border bg-white p-6">
    <p className="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-800">Fontes verificadas · Sem rankings</p><h3 className="text-2xl font-bold">Ações públicas, polêmicas e situação judicial</h3>
    <p className="my-4 text-sm leading-relaxed text-slate-600">Reportagens dão contexto; o estado de um processo exige fonte judicial. Benefícios e ações mostram a etapa documentada, sem presumir resultados para a população.</p>
    <button className="rounded-xl border px-4 py-3 text-sm font-semibold" disabled={busy} onClick={() => void load()}>{busy ? "Consultando registros…" : data ? "Consultar novamente" : "Consultar notícias e registros revisados"}</button>
    {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}
    {data && <div className="mt-6"><p className="text-sm leading-relaxed text-slate-500">{data.notice}</p><p className="mt-2 text-xs text-slate-500">Revisão editorial: {data.reviewed_at ? formatted(data.reviewed_at) : "Não realizada para este perfil"}. Não é monitoramento judicial em tempo real.</p>
      <h4 className="mb-3 mt-6 text-lg font-bold">Ações e benefícios noticiados</h4>
      {!data.actions.length && <p className="text-sm text-slate-500">Nenhuma ação pública revisada cadastrada para este perfil.</p>}
      <div className="space-y-4">{data.actions.map(item => <article className="rounded-xl border p-5" key={item.title}><p className="mb-2 text-sm font-bold text-emerald-800">{stages[item.stage]} · {formatted(item.stage_as_of)}</p><h5 className="font-bold">{item.title}</h5><p className="mt-3 text-sm leading-relaxed text-slate-600">{item.summary}</p><p className="mt-2 text-xs leading-relaxed text-slate-500">{item.attribution}</p><Sources official={item.official_source} journalism={item.journalism} /></article>)}</div>
      <h4 className="mb-3 mt-6 text-lg font-bold">Polêmicas e processos documentados</h4>
      {!data.cases.length && <p className="text-sm text-slate-500">Nenhum caso judicial revisado cadastrado. Isso não significa ausência de processos ou condenações.</p>}
      <div className="space-y-4">{data.cases.map(item => <article className="rounded-xl border p-5" key={item.case_number}><p className="mb-2 text-sm font-bold">{statuses[item.status]}</p><h5 className="font-bold">{item.title}</h5><p className="mt-3 text-sm leading-relaxed text-slate-600">{item.summary}</p><p className="mt-3 text-xs text-slate-500">Natureza: {item.category} · {item.court}</p><p className="mt-2 break-words text-xs text-slate-500">Processo: {item.case_number}</p><p className="mt-2 text-xs text-slate-500">Estado documentado em {formatted(item.status_as_of)}. {item.final_judgment ? "Trânsito em julgado informado pela fonte." : "Trânsito em julgado não confirmado nesta revisão."}</p><Sources official={item.official_source} journalism={item.journalism} /></article>)}</div>
    </div>}
  </section>;
}
