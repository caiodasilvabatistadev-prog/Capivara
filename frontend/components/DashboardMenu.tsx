"use client";
import type { Politician } from "../lib/api";

type Item = readonly [string, string, string, string, "disponível" | "parcial"];
const common: Item[] = [
  ["◎", "Biografia", "Trajetória com fonte identificada", "perfil-biografia", "disponível"],
  ["▤", "Bens declarados", "Declaração feita em uma eleição", "perfil-bens", "parcial"],
  ["⌘", "Família e carreira", "Parentescos, profissões e cargos", "perfil-familia", "parcial"],
  ["!", "Notícias e Justiça", "Contexto público e situação judicial", "public-context", "parcial"],
];
const byPower: Record<string, Item[]> = {
  legislativo: [
    ["$", "Despesas públicas", "Cotas, gabinete e recursos", "perfil-financas", "disponível"],
    ["⇄", "Emendas parlamentares", "Destinos e etapas dos recursos", "perfil-emendas", "parcial"],
    ["✓", "Projetos e relatorias", "Propostas de autoria e relatorias", "perfil-atividade", "disponível"],
    ["⚖", "Como votou", "Posições em votações nominais", "perfil-votacoes", "disponível"],
    ["◷", "Presença", "Presenças e ausências publicadas", "perfil-presenca", "disponível"],
  ],
  executivo: [
    ["✓", "Atos e entregas", "Leis sancionadas, obras e programas citados em fonte oficial", "perfil-executivo", "parcial"],
    ["$", "Recursos administrados", "Orçamento do órgão, sem tratar como gasto pessoal", "perfil-financas", "parcial"],
    ["◷", "Agenda pública", "Compromissos divulgados pelo órgão", "perfil-presenca", "parcial"],
  ],
  judiciario: [
    ["⚖", "Decisões e atuação", "Competência, decisões e funções oficiais", "perfil-atividade", "parcial"],
    ["$", "Remuneração e benefícios", "Dados funcionais publicados oficialmente", "perfil-financas", "parcial"],
    ["◷", "Agenda e sessões", "Participação institucional publicada", "perfil-presenca", "parcial"],
  ],
};

export default function DashboardMenu({ person }: { person?: Politician }) {
  const power = person?.power || "legislativo";
  const items = [common[0], ...(byPower[power] || []), ...common.slice(1)];
  function open(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }); }
  return <nav aria-label="Consultas disponíveis no perfil" className="mb-10 rounded-2xl border bg-white p-6">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Painel do {power === "judiciario" ? "Judiciário" : power === "executivo" ? "Executivo" : "Legislativo"}</p>
    <h3 className="mt-2 text-2xl font-bold">Dados organizados pela função do cargo</h3>
    <p className="mt-2 text-sm text-slate-600">Cada poder tem competências diferentes. Um indicador só aparece como resultado pessoal quando a fonte permite essa atribuição.</p>
    <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{items.map(([icon, title, description, id, status]) => <button className="dashboard-menu-card min-h-40 rounded-xl border bg-slate-50 p-4 text-left transition hover:-translate-y-0.5 hover:border-emerald-500" key={id} onClick={() => open(id)} type="button"><span aria-hidden="true" className="text-2xl font-bold text-emerald-800">{icon}</span><span className="mt-3 block font-bold leading-tight">{title}</span><span className="mt-2 block text-xs leading-relaxed text-slate-600">{description}</span><span className={`mt-3 inline-block rounded-full px-2 py-1 text-[10px] font-bold uppercase ${status === "disponível" ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"}`}>{status}</span></button>)}</div>
  </nav>;
}
