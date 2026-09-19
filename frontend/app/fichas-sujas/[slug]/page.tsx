import Link from "next/link";
import { notFound } from "next/navigation";
import Header from "../../../components/Header";
import { dirtyRecords } from "../../../lib/dirtyRecords";

export function generateStaticParams() { return dirtyRecords.map(item => ({ slug: item.slug })); }

export default async function DirtyRecordProfile({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params; const item = dirtyRecords.find(record => record.slug === slug); if (!item) notFound();
  return <><Header /><main className="mx-auto max-w-5xl px-5 py-10 sm:px-8"><Link className="font-bold text-emerald-800 underline" href="/fichas-sujas">← Voltar para Fichas sujas</Link><article className="mt-6 overflow-hidden rounded-2xl border bg-white"><div className="grid md:grid-cols-[320px_1fr]"><div className="min-h-96 bg-slate-200 bg-no-repeat" style={{ backgroundImage: `url(\"${item.photo}\")`, backgroundPosition: item.photoPosition, backgroundSize: item.photoSize ?? "cover" }} role="img" aria-label={`Foto de ${item.name}`} /><div className="p-7"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Capivara documentada</p><h1 className="mt-2 text-4xl font-bold">{item.name}</h1><div className="mt-4 flex flex-wrap gap-2">{item.tags.map(tag => <span className={`rounded-full px-3 py-2 text-xs font-bold ${tag === "Inelegível" ? "bg-amber-950 text-amber-100" : "bg-red-950 text-red-100"}`} key={tag}>{tag}</span>)}</div><p className="mt-6 leading-relaxed text-slate-600">{item.detail}</p><div className="mt-5 space-y-3">{item.sources.map(source => <div className="flex flex-wrap items-center justify-between gap-3 text-sm" key={source.url}><span className="text-slate-500">{source.label} · {source.date}</span><a className="font-bold text-emerald-800 underline" href={source.url} target="_blank" rel="noreferrer">Abrir fonte oficial</a></div>)}</div></div></div></article><p className="mt-6 text-sm leading-relaxed text-slate-500">A situação pode mudar após novas decisões. Este perfil reproduz somente o estágio descrito nas fontes indicadas.</p></main></>;
}
