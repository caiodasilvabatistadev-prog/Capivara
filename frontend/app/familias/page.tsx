import Link from "next/link";
import Header from "../../components/Header";

const requirements = [
  ["Parentesco comprovado", "Pai, mãe, filho, cônjuge ou irmão somente com documento ou declaração referenciada."],
  ["Trajetória política", "Cargo, instituição, local, partido e datas de início e fim para cada integrante."],
  ["Tempo no poder", "Anos documentados em cargos políticos, sem somar duas vezes períodos simultâneos."],
  ["Profissão anterior", "Ocupação declarada e respectiva fonte, sem inferência pela formação ou sobrenome."],
];

export default function FamiliesPage() {
  return <><Header /><main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Concentração familiar do poder</p>
    <h1 className="mt-2 max-w-4xl text-4xl font-bold">Famílias na política brasileira</h1>
    <p className="mt-4 max-w-4xl text-lg leading-relaxed text-slate-600">Este levantamento conecta parentescos comprovados a mandatos e cargos documentados. O objetivo é permitir que a população avalie, com evidências, por quanto tempo diferentes famílias ocuparam espaços de poder.</p>
    <div className="mt-8 flex flex-wrap gap-3"><Link className="rounded-xl bg-emerald-900 px-5 py-4 font-semibold text-white" href="/#public-search">Pesquisar uma pessoa</Link><Link className="rounded-xl border px-5 py-4 font-semibold" href="/fontes">Ver fontes e critérios</Link></div>
    <section className="mt-12 rounded-2xl border bg-white p-6" aria-labelledby="family-where"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Consulta individual</p><h2 id="family-where" className="mt-2 text-2xl font-bold">A linhagem aparece no perfil da pessoa</h2><p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600">Pesquise um político ou uma autoridade. Quando houver parentescos revisados, a seção “Parentescos documentados” será exibida no perfil, ao lado das provas de cada vínculo. Assim, nomes de famílias não ficam expostos sem o contexto da pessoa consultada.</p></section>
    <section className="mt-14" aria-labelledby="family-method"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Como uma família entra no levantamento</p><h2 id="family-method" className="mt-2 text-3xl font-bold">Critérios de comprovação</h2><div className="mt-6 grid gap-4 sm:grid-cols-2">{requirements.map(([title, text]) => <article className="rounded-2xl border bg-white p-5" key={title}><h3 className="text-lg font-bold">{title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p></article>)}</div></section>
    <section className="mt-14 rounded-2xl border bg-white p-6" aria-labelledby="family-ranking"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Próxima etapa</p><h2 id="family-ranking" className="mt-2 text-2xl font-bold">Ranking histórico de famílias políticas</h2><p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600">O ranking será publicado quando o conjunto tiver cobertura e revisão suficientes. Cada posição mostrará integrantes, cargos, períodos, anos não sobrepostos e provas de parentesco. Uma lista incompleta não será apresentada como retrato definitivo do Brasil.</p><dl className="mt-6 grid gap-4 sm:grid-cols-3"><div className="rounded-xl bg-slate-50 p-4"><dt className="text-sm text-slate-500">Famílias revisadas</dt><dd className="mt-1 text-2xl font-bold">Em construção</dd></div><div className="rounded-xl bg-slate-50 p-4"><dt className="text-sm text-slate-500">Cobertura histórica</dt><dd className="mt-1 text-2xl font-bold">Em construção</dd></div><div className="rounded-xl bg-slate-50 p-4"><dt className="text-sm text-slate-500">Documentos ligados</dt><dd className="mt-1 text-2xl font-bold">Em construção</dd></div></dl></section>
    <section className="mt-10 rounded-2xl bg-amber-50 p-5 text-sm leading-relaxed text-amber-950"><strong>Regra contra conclusões falsas:</strong> sobrenome igual, cidade de origem, convivência partidária ou reportagem sem documentação não bastam para criar um vínculo familiar.</section>
  </main></>;
}
