"use client";

const items = [
  ["◎", "Biografia", "Trajetória e contexto jornalístico", "perfil-biografia"],
  ["$", "Despesas públicas", "Cotas, gastos e recursos", "perfil-financas"],
  ["▤", "Bens declarados", "Patrimônio informado à Justiça Eleitoral", "perfil-bens"],
  ["⇄", "Emendas parlamentares", "Destinos e etapas dos recursos", "perfil-emendas"],
  ["✓", "Projetos e atividade", "Propostas de autoria e relatorias", "perfil-atividade"],
  ["⚖", "Como votou", "Posições em votações nominais", "perfil-votacoes"],
  ["◷", "Presença", "Presenças e ausências publicadas", "perfil-presenca"],
  ["⌘", "Família e carreira", "Parentescos, profissões e mandatos", "perfil-familia"],
  ["!", "Notícias e Justiça", "Contexto público e situação judicial", "public-context"],
] as const;

export default function DashboardMenu() {
  function open(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  return <nav aria-label="Consultas disponíveis no perfil" className="mb-10 rounded-2xl border bg-white p-6">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Painel da capivara</p>
    <h3 className="mt-2 text-2xl font-bold">Consultas disponíveis</h3>
    <p className="mt-2 text-sm text-slate-500">Escolha um assunto para ir direto aos dados desta pessoa.</p>
    <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{items.map(([icon, title, description, id]) => <button className="dashboard-menu-card min-h-36 rounded-xl border bg-slate-50 p-4 text-left transition hover:-translate-y-0.5 hover:border-emerald-500" key={id} onClick={() => open(id)} type="button"><span aria-hidden="true" className="text-2xl font-bold text-emerald-800">{icon}</span><span className="mt-3 block font-bold leading-tight">{title}</span><span className="mt-2 block text-xs leading-relaxed text-slate-500">{description}</span></button>)}</div>
  </nav>;
}
