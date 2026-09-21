"use client";
import { useState } from "react";
import { request, type Politician, type DashboardData } from "../lib/api";
import GlossaryTerm from "./GlossaryTerm";
type Section = DashboardData["sections"][number];
const topics = ["Todos", "Saúde", "Educação", "Segurança", "Trabalho", "Impostos", "Ambiente"];
const keywords: Record<string, string[]> = { Saúde: ["saude", "hospital", "sanitar"], Educação: ["educacao", "ensino", "escola"], Segurança: ["seguranca", "crime", "policia", "penal"], Trabalho: ["trabalh", "emprego", "previdencia"], Impostos: ["imposto", "tribut", "contribuicao", "fiscal"], Ambiente: ["ambient", "florest", "clima"] };
const folded = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
function publicSubject(row: string[]) {
  const original = `${row[1] || ""} ${row[2] || ""}`.trim();
  const value = folded(original);
  if (/^msf\s+\d+\/\d+/i.test(row[1] || "")) {
    const tail = (row[1] || "").split(/\s[-—]\s/).at(-1)?.replace(/\.$/, "") || "";
    const appointment = tail.match(/^(.*?)\s+\(([^)]+)\)$/);
    if (appointment) {
      const [, name, destination] = appointment;
      return folded(destination) === "onu"
        ? `Indicação de ${name} para representar o Brasil na ONU`
        : `Indicação de ${name} para embaixador do Brasil na ${destination}`;
    }
    return "Indicação de autoridade enviada ao Senado";
  }
  const publicChoice = (row[2] || "").match(/escolhe o senhor (.+?) para o cargo de (.+?)(?:,| nos termos)/i);
  if (publicChoice) return `Escolha de ${publicChoice[1]} para ${publicChoice[2]}`;
  if (/maconha|cannabis/.test(value)) {
    if (/medicin|terapeut/.test(value)) return "Uso medicinal da cannabis";
    if (/legaliz|regulament|descriminaliz/.test(value)) return "Legalização ou regulamentação da maconha";
    return "Política sobre maconha e cannabis";
  }
  if (/aborto|interrupcao da gravidez/.test(value)) return "Regras sobre aborto";
  if (/reforma tributaria|tributacao|imposto/.test(value)) return "Impostos e reforma tributária";
  if (/aposentadoria|previdencia/.test(value)) return "Aposentadoria e Previdência";
  if (/arma de fogo|porte de arma|posse de arma/.test(value)) return "Posse e porte de armas";
  if (/educacao|ensino|escola/.test(value)) return "Educação e ensino";
  if (/saude|hospital|sus/.test(value)) return "Saúde pública";
  if (/meio ambiente|florest|clima/.test(value)) return "Meio ambiente e clima";
  const changedLaw = (row[2] || "").match(/altera.+?lei complementar n[º°]?\s*([\d.]+),?\s*de\s*(\d{4})/i);
  if (changedLaw) return `Mudança em regra da Lei Complementar nº ${changedLaw[1]}/${changedLaw[2]}`;
  return row[1] || "Assunto descrito pela fonte oficial";
}
function Panel({ person, kind, onLoaded, onClear }: { person: Politician; kind: "amendments" | "votes"; onLoaded: (data: Section) => void; onClear?: (title: string) => void }) {
  const [data, setData] = useState<Section | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [year, setYear] = useState(new Date().getUTCFullYear());
  const [days, setDays] = useState(90);
  const [topic, setTopic] = useState("Todos");
  const [query, setQuery] = useState("");
  const title = kind === "amendments" ? "Para onde foram as emendas?" : "Como votou nos assuntos da população?";
  const supported = ["camara", "senado"].includes(person.provider);
  async function load() {
    setBusy(true); setError(""); setData(null); onClear?.(kind === "amendments" ? "Destinos das emendas" : "Votos e assuntos em Plenário");
    try { const result = await request<Section>(`/politicians/${person.provider}/${person.id}/${kind}?${kind === "amendments" ? "year=" + year : "days=" + days}`); setData(result); onLoaded(result); }
    catch { setError("Não foi possível consultar este detalhamento. Tente novamente."); }
    finally { setBusy(false); }
  }
  const table = data?.blocks?.find(block => block.kind === "table");
  const rows = (table?.rows.slice(1) || []).filter(row => {
    const text = folded(row.slice(0, 3).join(" "));
    const explicitVote = kind !== "votes" || row[3] === "Sim" || row[3] === "Não";
    return explicitVote && text.includes(folded(query)) && (topic === "Todos" || (keywords[topic] || []).some(key => text.includes(key)));
  });
  return <section aria-label={title} className="mb-10 rounded-2xl border bg-white p-6">
    <p className="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-800">Dados oficiais · {kind === "amendments" ? <><GlossaryTerm term="Emenda Pix">Emendas Pix</GlossaryTerm>, destinação e execução</> : "Voto individual e contexto"}</p><h3 className="text-2xl font-bold">{title}</h3>
    {kind === "amendments" && <p className="mt-3 rounded-xl bg-emerald-50 p-4 text-sm leading-relaxed text-emerald-950"><strong>O que é Emenda Pix?</strong> É o nome popular da <GlossaryTerm term="Transferência especial" />: um parlamentar indica recursos enviados diretamente a um estado ou município. Aqui você vê quem indicou, quem recebeu, a finalidade informada e a etapa do dinheiro.</p>}
    <p className="my-4 text-sm leading-relaxed text-slate-600">{kind === "amendments" ? "Veja as Transferências Especiais, conhecidas como Emendas Pix, com ente beneficiário, finalidade, valores previstos e empenhados. Para deputados, a consulta também reúne as demais emendas publicadas pela Câmara." : "O assunto aparece primeiro em linguagem simples, seguido do voto e do texto original. Esta lista mostra somente votos individuais registrados como Sim ou Não."}</p>
    {!supported ? <p className="text-sm text-slate-500">Emendas de autoria parlamentar e votos em Plenário não se aplicam a este cargo.</p> : <>
      <div className="parliament-controls flex flex-wrap items-center gap-3">
        {kind === "amendments" ? <label className="text-sm">Ano das emendas<select aria-label="Ano das emendas" disabled={busy} className="ml-3 rounded-lg border bg-slate-50 p-2" value={year} onChange={event => { setYear(Number(event.target.value)); setData(null); onClear?.("Destinos das emendas"); }}>{Array.from({ length: new Date().getUTCFullYear() - 2023 }, (_, i) => new Date().getUTCFullYear() - i).map(value => <option key={value}>{value}</option>)}</select></label> : <label className="text-sm">Período das votações<select aria-label="Período das votações" disabled={busy} className="ml-3 rounded-lg border bg-slate-50 p-2" value={days} onChange={event => { setDays(Number(event.target.value)); setData(null); onClear?.("Votos e assuntos em Plenário"); }}><option value={30}>Últimos 30 dias</option><option value={90}>Últimos 90 dias</option><option value={365}>Últimos 365 dias</option></select></label>}
        <button className="rounded-xl border px-4 py-3 text-sm font-semibold" disabled={busy} onClick={() => void load()}>{busy ? "Consultando detalhamento…" : kind === "amendments" ? "Consultar emendas e Emendas Pix" : "Consultar votos individuais"}</button>
      </div>
      {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}
      {data && Array.isArray(data.blocks) && <div className="mt-5">
        {data.blocks.filter(block => block.kind === "text").map(block => <p key={block.text} className="mb-3 break-words text-xs leading-relaxed text-slate-500">{block.text}</p>)}
        <div className="parliament-controls mb-5 mt-5"><label className="text-sm font-semibold">Filtrar por assunto ou localidade<input className="mt-2 block w-full rounded-xl border bg-slate-50 p-3 font-normal" value={query} onChange={event => setQuery(event.target.value)} placeholder="Ex.: saúde, imposto ou nome do município" /></label>
          {kind === "votes" && <><p className="my-3 text-xs text-slate-500">Atalhos por palavras no contexto publicado; não são classificação oficial nem avaliação do voto.</p><div className="flex flex-wrap gap-2">{topics.map(value => <button key={value} aria-pressed={topic === value} onClick={() => setTopic(value)} className={"scope rounded-lg border px-3 py-2 text-xs " + (topic === value ? "scope-selected" : "")}>{value}</button>)}</div></>}
        </div>
        <p className="mb-4 text-xs text-slate-500">{rows.length} registro(s) exibido(s). O PDF inclui todo o detalhamento consultado, sem os filtros de tela.</p>
        {!rows.length && <p className="text-sm">Nenhum registro neste recorte. Isso não comprova ausência de destinações ou participação.</p>}
        <div className="grid gap-4 lg:grid-cols-2">{rows.map((row, index) => <article key={index} className="rounded-xl border p-5">
          {kind === "amendments" ? <><p className="mb-2 text-xs font-semibold text-emerald-800">{row[0].includes("Emenda Pix") ? <GlossaryTerm term="Emenda Pix">{row[0]}</GlossaryTerm> : row[0]}</p><h4 className="font-bold leading-relaxed">{row[1]}</h4><dl className="mt-5 space-y-3">{row.slice(2).map((value, i) => { const label = table?.rows[0][i + 2] || ""; const term = label.startsWith("Previsto") ? "Valor previsto" : label; return <div key={i} className="flex flex-wrap justify-between gap-2 text-sm"><dt className="text-slate-500"><GlossaryTerm term={term}>{label}</GlossaryTerm></dt><dd className="font-bold">{value}</dd></div>; })}</dl></> : <><p className="text-xs font-bold uppercase tracking-widest text-slate-500">Assunto para a população</p><h4 className="mb-4 mt-1 text-xl font-bold leading-tight text-slate-950">{publicSubject(row)}</h4><p className="mb-3 rounded-lg bg-emerald-50 p-3 text-sm font-bold text-emerald-900">Como votou: {row[3] === "Sim" ? "Sim — a favor do objeto votado" : row[3] === "Não" ? "Não — contra o objeto votado" : row[3]}</p><p className="mb-2 text-xs text-slate-500">{row[0]}</p><p className="font-semibold leading-relaxed">Texto original: {row[1]}</p><p className="mt-3 text-sm leading-relaxed text-slate-600">{row[2]}</p><details className="mt-4 text-xs"><summary className="cursor-pointer font-semibold">Fonte da votação</summary><p className="mt-2 break-all text-slate-500">{row[4]}</p></details></>}
        </article>)}</div>
      </div>}
    </>}
  </section>;
}
export default function ParliamentRecords({ person, onLoaded, onClear, show = "all" }: { person: Politician; onLoaded: (data: Section) => void; onClear?: (title: string) => void; show?: "all" | "amendments" | "votes" }) {
  return <>{show !== "votes" && <Panel person={person} kind="amendments" onLoaded={onLoaded} onClear={onClear} />}{show !== "amendments" && <Panel person={person} kind="votes" onLoaded={onLoaded} onClear={onClear} />}</>;
}
