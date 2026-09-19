import Link from "next/link";
import Header from "../../components/Header";
import { dirtyRecords } from "../../lib/dirtyRecords";

export default function DirtyRecordsPage() {
  return <><Header /><main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Decisões oficiais vigentes</p><h1 className="mt-2 text-4xl font-bold">Fichas sujas</h1>
    <p className="mt-4 max-w-4xl text-lg leading-relaxed text-slate-600">Inelegíveis por decisão eleitoral e condenados cujo cumprimento da prisão foi confirmado. Clique em um cartão para puxar a capivara.</p>
    <div className="mt-6 rounded-2xl border border-amber-700 bg-amber-950 p-5 text-sm leading-relaxed text-amber-100"><strong>Selos:</strong> “Inelegível” não significa prisão. Preso, semiaberto, domiciliar e condicional só aparecem quando a fonte oficial confirma o regime atual.</div>
    <section className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-label="Pessoas com situação oficial documentada">{dirtyRecords.map(item => <Link className="group aspect-square overflow-hidden rounded-2xl border bg-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-400" href={`/fichas-sujas/${item.slug}`} key={item.slug} aria-label={`Puxar a capivara de ${item.name}`}>
      <article className="flex h-full flex-col"><div className="h-[58%] shrink-0 bg-slate-200 bg-no-repeat transition-transform duration-200 group-hover:scale-[1.02]" style={{ backgroundImage: `linear-gradient(to top, #0d1623 0%, transparent 45%), url(\"${item.photo}\")`, backgroundPosition: `center, ${item.photoPosition}`, backgroundSize: `100% 100%, ${item.photoSize ?? "cover"}` }} role="img" aria-label={`Foto de ${item.name}`} /><div className="relative flex min-h-0 flex-1 flex-col bg-white p-5"><h2 className="text-xl font-bold">{item.name}</h2><div className="mt-3 flex flex-wrap gap-2">{item.tags.map(tag => <span className={`rounded-full px-3 py-1 text-xs font-bold ${tag === "Inelegível" ? "bg-amber-950 text-amber-100" : "bg-red-950 text-red-100"}`} key={tag}>{tag}</span>)}</div><p className="mt-auto pt-3 text-sm font-bold text-emerald-800">Puxar a capivara →</p></div></article>
    </Link>)}</section>
    <p className="mt-8 text-sm leading-relaxed text-slate-500">Lista inicial com revisão manual. A ausência de um nome não comprova elegibilidade nem inexistência de condenação.</p>
  </main></>;
}
