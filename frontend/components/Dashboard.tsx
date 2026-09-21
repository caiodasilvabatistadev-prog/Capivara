"use client";
import ParliamentRecords from "./ParliamentRecords";
import News from "./News";
import PublicContext, { contextBlocks, type Context } from "./PublicContext";
import { useEffect, useRef, useState } from "react";
import { type DashboardData, type ReportBlock, downloadPdf } from "../lib/api";
import Portrait from "./Portrait";
import GlossaryTerm from "./GlossaryTerm";
import Biography from "./Biography";
import Assets from "./Assets";
import PoliticalFamily from "./PoliticalFamily";
import Career from "./Career";
import Newsletter from "./Newsletter";
import Proposals from "./Proposals";
import DashboardMenu from "./DashboardMenu";
import PowerScope from "./PowerScope";
import ExecutiveActions from "./ExecutiveActions";

const labels: Record<string, string> = {
  "Presença em Plenário - Presenças na Câmara": "Dias em Plenário",
  "Presença em Plenário - Ausências justificadas": "Ausências justificadas no Plenário",
  "Presença em Plenário - Ausências não justificadas": "Ausências não justificadas no Plenário",
  "Presença em Comissões - Presenças na Câmara": "Reuniões em comissões",
  "Presença em Comissões - Ausências justificadas": "Ausências justificadas em comissões",
  "Presença em Comissões - Ausências não justificadas": "Ausências não justificadas em comissões",
  "Propostas legislativas - de sua autoria": "Propostas de sua autoria",
  "Propostas legislativas - relatadas": "Propostas relatadas",
  "Votações nominais - em Plenário": "Votações nominais em Plenário",
  "Discursos - em Plenário": "Discursos em Plenário",
};

function Block({ block }: { block: ReportBlock }) {
  if (block.kind === "table") return <div className="my-5 overflow-x-auto"><p className="mb-3 font-semibold">{block.text}</p><table className="w-full text-left text-sm"><thead><tr>{block.rows[0]?.map((cell, i) => <th className="border-b bg-slate-50 p-3" key={i} scope="col"><GlossaryTerm term={cell}>{cell}</GlossaryTerm></th>)}</tr></thead><tbody>{block.rows.slice(1).map((row, i) => <tr className="border-b" key={i}>{row.map((cell, j) => <td className="p-3" key={j}>{cell}</td>)}</tr>)}</tbody></table></div>;
  if (block.kind === "heading") return <h3 className="mb-3 mt-5 font-bold text-slate-900">{block.text}</h3>;
  return <p className="my-2 leading-relaxed text-slate-600">{block.text}</p>;
}

export default function Dashboard({ data, onBack }: { data: DashboardData; onBack: () => void }) {
  const [parliament, setParliament] = useState<DashboardData["sections"]>([]);
  const [context, setContext] = useState<Context | null>(null);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const person = data.politician;
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => { title.current?.focus(); }, [data]);
  const groupPriority = ["Gastos públicos", "Recursos públicos", "Equipe", "Atividade legislativa", "Propostas legislativas", "Votações", "Discursos", "Presença"];
  const groups = [...new Set(data.metrics.map(metric => metric.group))].sort((a, b) => {
    const first = groupPriority.indexOf(a); const second = groupPriority.indexOf(b);
    return (first < 0 ? 999 : first) - (second < 0 ? 999 : second);
  });
  const monthly = data.sections.flatMap(section => section.blocks).find(block => block.kind === "table" && block.text.includes("Gasto mensal da cota parlamentar"));
  const months = (monthly?.rows.slice(1) || []).map(row => ({ month: row[0], label: row[1], amount: Number(row[1]?.replaceAll(".", "").replace(",", ".")) })).filter(row => Number.isFinite(row.amount));
  const maximum = Math.max(1, ...months.map(row => row.amount));
  const amendments = data.sections.flatMap(section => section.blocks).filter(block => block.kind === "table" && block.text.startsWith("Emenda: "));
  const financialGroups = groups.filter(group => ["Gastos públicos", "Recursos públicos", "Equipe"].includes(group));
  const legislativeGroups = groups.filter(group => ["Atividade legislativa", "Propostas legislativas", "Votações", "Discursos"].includes(group));
  const attendanceGroups = groups.filter(group => group === "Presença");
  const remainingGroups = groups.filter(group => ![...financialGroups, ...legislativeGroups, ...attendanceGroups].includes(group));
  function renderGroup(group: string) {
    return <div key={group}><section aria-label={group} className="mb-10"><h3 className="mb-4 text-xl font-bold">{group}</h3><div className={`grid gap-4 sm:grid-cols-2 ${group === "Gastos públicos" ? "" : "lg:grid-cols-3"}`}>{data.metrics.filter(metric => metric.group === group).map(metric => { const label = labels[metric.label] || metric.label; return <article className="rounded-2xl border bg-white p-5" key={metric.label}><h4 className="mb-3 text-sm font-semibold text-slate-600"><GlossaryTerm term={label}>{label}</GlossaryTerm></h4><p className={"break-words font-bold tracking-tight text-emerald-950 " + (metric.value.length > 80 ? "text-base leading-relaxed" : "text-2xl")}>{metric.value.replace(/^1 dias$/, "1 dia").replace(/^1 reuniões$/, "1 reunião")}</p><p className="mt-3 text-xs leading-relaxed text-slate-500">{metric.explanation}</p></article>; })}</div></section>{group === "Atividade legislativa" && <Proposals person={person} initialYear={data.year} onLoaded={section => setParliament(old => [...old.filter(item => item.title !== section.title), section])} />}</div>;
  }
  async function exportPdf() {
    setExporting(true); setError("");
    try { await downloadPdf({ ...data, sections: [...data.sections, ...parliament, ...(context ? [{ title: "Notícias e situação judicial", blocks: contextBlocks(context) }] : [])] }); } catch (error) { setError((error as Error).message); }
    finally { setExporting(false); }
  }
  return <section id={`perfil-${person.provider}-${person.id}`} aria-label="Perfil" className="mt-8">
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <button className="text-sm font-semibold text-emerald-900 underline" onClick={onBack}>Voltar aos resultados</button>
      <div className="flex flex-wrap gap-3"><button className="rounded-xl border bg-white px-4 py-3 text-sm font-semibold" onClick={() => document.getElementById("public-context")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Notícias e situação judicial</button><button className="rounded-xl border bg-white px-4 py-3 text-sm font-semibold" onClick={() => window.print()}>Imprimir a capivara</button><button disabled={exporting} className="rounded-xl bg-emerald-900 px-4 py-3 text-sm font-semibold text-white" onClick={() => void exportPdf()}>{exporting ? "Gerando PDF…" : "Baixar PDF completo"}</button></div>
    </div>
    {error && <p role="alert" className="mb-5 text-red-700">{error}</p>}
    <header className="rounded-2xl border bg-white p-7 sm:flex sm:items-center sm:gap-6">
      <Portrait person={person} size="profile" />
      <div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">{person.role || "Deputado federal"} · {person.state}</p><h2 ref={title} tabIndex={-1} className="text-3xl font-bold">{person.name}</h2><p className="mt-2 text-slate-600">{person.party} · {person.email || "E-mail não informado"}</p><p className="mt-3 text-sm font-medium text-emerald-800">Dados oficiais consultados {person.provider === "camara" ? "na Câmara dos Deputados" : "no órgão: " + person.institution}.</p></div>
    </header>
    <aside aria-label={`Perfil em leitura: ${person.name}`} className="profile-reading sticky top-24 z-30 ml-auto mt-3 flex w-fit max-w-full items-center gap-3 rounded-2xl border p-2 pr-4 shadow-lg backdrop-blur print:hidden">
      <Portrait person={person} size="compact" /><div className="min-w-0"><p className="truncate text-sm font-bold">{person.name}</p><p className="truncate text-xs text-slate-500">{person.role || "Representante"} · {person.party || "Partido não informado"}</p></div>
    </aside>
    <div className="my-5 flex flex-wrap justify-between gap-2 text-sm text-slate-600"><p>Período dos indicadores: <strong>{data.year || "Não informado"}</strong></p><p>Consulta: {new Date(data.fetched_at).toLocaleString("pt-BR")}</p></div>
    <p className="mb-8 rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-relaxed text-emerald-950">{data.notice}</p>
    <PowerScope person={person} />
    <DashboardMenu person={person} />
    <div id="perfil-biografia" className="scroll-mt-32"><Biography person={person} /></div>
    <div id="perfil-bens" className="scroll-mt-32"><Assets person={person} /></div>
    <ExecutiveActions data={data} />
    <div id="perfil-financas" className="scroll-mt-32">{financialGroups.map(renderGroup)}</div>
    {months.length > 0 && <section aria-label="Gasto mensal" className="mb-10 rounded-2xl border bg-white p-6"><h3 className="text-xl font-bold">Cota parlamentar por mês</h3><p className="mb-6 mt-2 text-sm text-slate-500">Valores publicados por {person.institution || "Câmara dos Deputados"}. As barras comparam os meses, sem indicar limite de gastos.</p><div className="space-y-4">{months.map(row => <div className="grid grid-cols-[2.5rem_1fr_8rem] items-center gap-3 text-sm" key={row.month}><span>{row.month}</span><div aria-hidden="true" className="h-3 rounded-full bg-emerald-50"><div className="h-3 rounded-full bg-emerald-700" style={{ width: `${100 * row.amount / maximum}%` }} /></div><span className="text-right font-medium">R$ {row.label}</span></div>)}</div></section>}
    {amendments.length > 0 && <section aria-label="Emendas para a população" className="mb-10"><h3 className="text-xl font-bold">Emendas para estados e municípios</h3><p className="mb-5 mt-2 text-sm text-slate-600">Destinações destacadas na página oficial. Autorizado é previsão no orçamento; empenhado é reservado; pago é transferido. Não somamos essas etapas.</p><div className="grid gap-4 lg:grid-cols-3">{amendments.map(block => <article className="rounded-2xl border bg-white p-5" key={block.text}><h4 className="mb-5 font-semibold leading-relaxed">{block.text.slice(8)}</h4><dl className="space-y-3">{block.rows.slice(1).map((row, i) => <div className="flex flex-wrap justify-between gap-2 text-sm" key={i}><dt className="text-slate-500">{row[0]}</dt><dd className="font-bold">{row[1]}</dd></div>)}</dl></article>)}</div></section>}
    <div id="perfil-emendas" className="scroll-mt-32"><ParliamentRecords person={person} show="amendments" onClear={title => setParliament(old => old.filter(item => item.title !== title))} onLoaded={section => setParliament(old => [...old.filter(item => item.title !== section.title), section])} /></div>
    <div id="perfil-atividade" className="scroll-mt-32">{legislativeGroups.map(renderGroup)}</div>
    <div id="perfil-votacoes" className="scroll-mt-32"><ParliamentRecords person={person} show="votes" onClear={title => setParliament(old => old.filter(item => item.title !== title))} onLoaded={section => setParliament(old => [...old.filter(item => item.title !== section.title), section])} /></div>
    <div id="perfil-presenca" className="scroll-mt-32">{attendanceGroups.map(renderGroup)}</div>
    <div id="perfil-familia" className="scroll-mt-32"><Career person={person} /><PoliticalFamily person={person} /></div>
    {remainingGroups.map(renderGroup)}
    <PublicContext key={person.provider + "-" + person.id} person={person} onLoaded={setContext} />
    <News key={"news-" + person.provider + "-" + person.id} person={person} />
    <Newsletter person={person} />
    <h3 className="mb-4 text-xl font-bold">Dados e detalhes da fonte</h3><p className="mb-5 text-sm text-slate-600">Abra uma seção para ler os dados disponíveis nesta integração sem sair daqui. Percentuais das tabelas são reproduzidos como publicados; eventuais inconsistências pertencem à fonte.</p>
    <div className="space-y-3">{data.sections.map(section => <details className="rounded-xl border bg-white p-5" key={section.title}><summary className="cursor-pointer font-semibold">{section.title}</summary><div className="mt-5 text-sm">{section.blocks.map((block, i) => <Block block={block} key={i} />)}</div></details>)}</div>
    <div className="mt-6 text-xs leading-relaxed text-slate-500">{data.updates.map(update => <p key={update}>{update}</p>)}<p className="mt-2">Os dados podem ter períodos de atualização diferentes. Não informado não significa ausência de atividade.</p></div>
  </section>;
}
