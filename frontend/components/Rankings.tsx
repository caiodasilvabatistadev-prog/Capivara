"use client";
import Image from "next/image";
import { useState } from "react";
import { request } from "../lib/api";
import Portrait from "./Portrait";
import GlossaryTerm from "./GlossaryTerm";

export type Ranking = {
  provider: string; metric: string; year: number; status: "ready" | "partial" | "unavailable" | "not_applicable";
  title: string; unit: string; notice: string; source_url: string; source_as_of: string | null;
  fetched_at: string; covered: number; total: number | null;
  entries: { position: number; id: number | null; name: string; photo_url?: string | null; value: string; detail: string; party?: { id: number; sigla: string; president: string; logo_url: string; background?: string; source_url: string; reviewed_at: string } | null }[];
};
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
function Card({ provider, metric, year, title, onOpen }: { provider: string; metric: string; year: number; title: string; onOpen: (provider: string, id: number) => void }) {
  const [data, setData] = useState<Ranking | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load() {
    setBusy(true); setError("");
    try { setData(await request<Ranking>(`/rankings?provider=${provider}&metric=${metric}&year=${year}`)); }
    catch { setError("Não foi possível consultar esta fonte. Tente novamente."); }
    finally { setBusy(false); }
  }
  return <article className="min-w-0 rounded-2xl border bg-white p-5">
    <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">{year} · {metric.includes("fund") ? "Partidos · Nacional" : provider === "camara" ? "Câmara dos Deputados" : provider === "senado" ? "Senado Federal" : provider === "judiciario" ? "Judiciário" : "Executivo"}</p>
    <h3 className="text-xl font-bold"><GlossaryTerm term={title.startsWith("Fundo Partidário") ? "Fundo Partidário" : title.startsWith("Fundo Eleitoral") ? "Fundo Eleitoral" : title}>{title}</GlossaryTerm></h3>
    {metric === "approved" && <p className="mt-3 text-xs leading-relaxed text-slate-500">Em preparação: ainda sem levantamento validado de aprovação final e autoria. Projetos apresentados não são usados como substituto.</p>}
    {metric === "absences" && provider === "camara" && <p className="mt-3 text-xs leading-relaxed text-slate-500">Consulta os perfis oficiais. Pode levar até três minutos; eventuais falhas serão informadas como cobertura parcial.</p>}
    <button disabled={busy} onClick={() => void load()} className="mt-4 rounded-xl border px-4 py-3 text-sm font-semibold">{busy ? "Consultando…" : data ? "Atualizar comparação" : "Consultar comparação"}</button>
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    {data && <div className="mt-5">
      {data.status === "partial" && <p className="mb-4 rounded-lg border p-3 text-sm font-bold">Cobertura parcial: {data.covered} de {data.total} perfis. Esta ordem representa somente os dados consultados.</p>}
      {data.status === "unavailable" && <p className="mb-3 font-semibold">Dados ainda não disponíveis para esta comparação</p>}
      {data.status === "not_applicable" && <p className="mb-3 font-semibold">Indicador parlamentar não aplicável a este poder</p>}
      <p className="mb-4 text-xs leading-relaxed text-slate-500">{data.notice}</p>
      <ol className="space-y-3">{data.entries.map(item => <li className={"rounded-xl border bg-slate-50 p-4 " + (item.party ? "party-ranking" : "")} key={item.id || item.name}>
        {item.party && <div aria-hidden="true" className="party-logo" style={{ backgroundColor: item.party.background || "#203342" }}><Image src={item.party.logo_url} alt="" fill unoptimized sizes="240px" /></div>}
        <div className="relative z-10 flex items-start gap-3"><span className="text-sm font-bold text-emerald-800">{item.position}º</span>{item.id !== null && <Portrait person={{ id: item.id, provider, name: item.name, party: "", state: "", email: null, photo_url: item.photo_url, source_url: data.source_url }} size="compact" />}<div className="min-w-0 flex-1"><p className="break-words font-semibold">{item.name}</p><p className="mt-1 text-lg font-bold text-emerald-950">{data.unit === "BRL" ? money.format(Number(item.value)) : Number(item.value).toLocaleString("pt-BR") + " " + data.unit}</p>{item.detail && <p className="mt-2 text-xs leading-relaxed text-slate-500">{item.detail}</p>}
        {item.party && <p className="mt-3 text-xs leading-relaxed text-slate-500">Presidente nacional<br /><a className="party-president font-semibold text-emerald-800 underline underline-offset-4" href={`#perfil-partidos-${item.party.id}`} onClick={event => { event.preventDefault(); onOpen("partidos", item.party!.id); }}>{item.party.president}</a><span className="mt-2 block text-[10px]">TSE · conferido em {item.party.reviewed_at.split("-").reverse().join("/")}</span></p>}
        {item.id !== null && <button onClick={() => onOpen(provider, item.id!)} className="mt-3 text-xs font-bold text-emerald-800">Puxar a capivara de {item.name}</button>}</div></div>
      </li>)}</ol>
      {data.source_url && <details className="mt-5 text-xs text-slate-500"><summary className="cursor-pointer font-semibold">Fonte e período</summary><p className="mt-3 break-all">{data.source_url}</p><p className="mt-2">Ano: {data.year}{data.source_as_of ? " · Publicação: " + data.source_as_of.split("-").reverse().join("/") : " · Arquivo consultado agora"}</p><p className="mt-2">Cobertura: {data.covered} registros de pessoas ou partidos{data.total !== null ? " / " + data.total + " na referência" : " com dados no arquivo"}. Lista limitada aos dez primeiros; empates têm a mesma posição.</p></details>}
    </div>}
  </article>;
}
export default function Rankings({ provider: initialProvider, onOpen }: { provider?: string; onOpen: (provider: string, id: number) => void }) {
  const [provider, setProvider] = useState(initialProvider || "camara");
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  return <section aria-label="Rankings de dados públicos" className="mt-8">
    <div className="mb-5 flex flex-wrap items-center justify-between gap-4"><div><p className="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-800">Comparações com fonte e período</p><h2 className="text-2xl font-bold">O dinheiro e a atuação em números</h2></div><label className="text-sm font-semibold">Ano da atuação<select className="ml-3 rounded-lg border bg-slate-50 px-3 py-2" value={year} onChange={e => setYear(Number(e.target.value))}>{[currentYear, currentYear - 1].map(value => <option key={value}>{value}</option>)}</select></label></div>
    {!initialProvider && <label className="mb-5 block text-sm font-semibold">Comparação parlamentar<select className="ml-3 rounded-lg border bg-slate-50 px-3 py-2" value={provider} onChange={event => setProvider(event.target.value)}><option value="camara">Câmara dos Deputados</option><option value="senado">Senado Federal</option></select></label>}
    <p className="mb-5 text-sm leading-relaxed text-slate-500">As comparações parlamentares têm sua própria seleção de Câmara ou Senado. Gastos, projetos e faltas são indicadores distintos; não formam uma nota política. Os dados são consultados quando você abre cada lista.</p>
    <div className="grid items-start gap-4 md:grid-cols-2">{[["amendments", "Mais emendas individuais empenhadas"], ["expenses", "Maiores gastos com cota parlamentar"], ["approved", "Mais projetos aprovados"], ["absences", "Maiores ausências em Plenário"]].map(([metric, title]) => <Card key={provider + metric + year} provider={provider} metric={metric} year={year} title={title} onOpen={onOpen} />)}</div>
    <h3 className="mb-2 mt-8 text-xl font-bold">Recursos dos partidos — âmbito nacional</h3><p className="mb-5 text-sm leading-relaxed text-slate-500">Os fundos pertencem aos partidos, sem divisão por poder. Fundo Partidário: balanço fechado de 2025. Fundo Eleitoral: valores destinados para 2026, que não comprovam recebimento pelas candidaturas.</p>
    <div className="grid items-start gap-4 lg:grid-cols-2"><Card provider="camara" metric="party_fund" year={2025} title="Fundo Partidário — maiores repasses" onOpen={onOpen} /><Card provider="camara" metric="election_fund" year={2026} title="Fundo Eleitoral — maiores valores destinados" onOpen={onOpen} /></div>
  </section>;
}
