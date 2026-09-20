"use client";

import Link from "next/link";
import { useState } from "react";
import { dirtyRecords } from "../lib/dirtyRecords";

export default function DirtyRecordsGrid() {
  const [filter, setFilter] = useState<"todos" | "vivos" | "falecidos">("todos");
  const items = dirtyRecords.filter(item => filter === "todos" || (filter === "falecidos" ? item.lifeStatus === "falecido" : item.lifeStatus !== "falecido"));
  return <>
    <div className="mt-8 flex flex-wrap gap-2" aria-label="Filtrar fichas sujas">
      {(["todos", "vivos", "falecidos"] as const).map(value => <button aria-pressed={filter === value} className={`rounded-full border px-4 py-2 text-sm font-bold ${filter === value ? "bg-emerald-700 text-white" : "bg-white text-slate-900"}`} key={value} onClick={() => setFilter(value)} type="button">{value === "todos" ? "Todos" : value === "vivos" ? "Pessoas vivas" : "Pessoas falecidas"}</button>)}
    </div>
    <section className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-label="Pessoas com situação oficial documentada">{items.map(item => <Link className="group aspect-square overflow-hidden rounded-2xl border bg-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-400" href={`/fichas-sujas/${item.slug}`} key={item.slug} aria-label={`Puxar a capivara de ${item.name}`}>
      <article className="flex h-full flex-col"><div className="h-[58%] shrink-0 bg-slate-200 bg-no-repeat transition-transform duration-200 group-hover:scale-[1.02]" style={{ backgroundImage: `linear-gradient(to top, #0d1623 0%, transparent 45%), url(\"${item.photo}\")`, backgroundPosition: `center, ${item.photoPosition}`, backgroundSize: `100% 100%, ${item.photoSize ?? "cover"}` }} role="img" aria-label={`Foto de ${item.name}`} /><div className="relative flex min-h-0 flex-1 flex-col bg-white p-5"><h2 className="text-xl font-bold">{item.name}</h2><div className="mt-3 flex flex-wrap gap-2">{item.tags.map(tag => <span className={`rounded-full px-3 py-1 text-xs font-bold ${tag === "Inelegível" ? "bg-amber-950 text-amber-100" : "bg-red-950 text-red-100"}`} key={tag}>{tag}</span>)}</div><p className="mt-auto pt-3 text-sm font-bold text-emerald-800">Puxar a capivara →</p></div></article>
    </Link>)}</section>
  </>;
}
