"use client";
import { useRouter } from "next/navigation";
import Header from "../../components/Header";
import Rankings from "../../components/Rankings";
import HouseComposition from "../../components/HouseComposition";
import Demographics from "../../components/Demographics";
import Newsletter from "../../components/Newsletter";

export default function RankingsPage() {
  const router = useRouter();
  return <><Header /><main className="mx-auto max-w-6xl px-5 py-10 sm:px-8"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Retrato da política hoje</p><h1 className="mt-2 text-4xl font-bold">Rankings e gráficos públicos</h1><p className="mt-4 max-w-3xl leading-relaxed text-slate-600">Compare recursos, atuação parlamentar, composição dos plenários e representatividade. Cada painel informa fonte, período e limites.</p><Rankings onOpen={(source, id) => router.push(`/?provider=${source}&id=${id}`)} /><HouseComposition /><Demographics /><Newsletter /></main></>;
}
