import Header from "../../components/Header";
import DirtyRecordsGrid from "../../components/DirtyRecordsGrid";

export default function DirtyRecordsPage() {
  return <><Header /><main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Decisões oficiais vigentes</p><h1 className="mt-2 text-4xl font-bold">Fichas sujas</h1>
    <p className="mt-4 max-w-4xl text-lg leading-relaxed text-slate-600">Inelegíveis por decisão eleitoral e condenados cujo cumprimento da prisão foi confirmado. Clique em um cartão para puxar a capivara.</p>
    <div className="mt-6 rounded-2xl border border-amber-700 bg-amber-950 p-5 text-sm leading-relaxed text-amber-100"><strong>Selos:</strong> “Inelegível” não significa prisão. Preso, semiaberto, domiciliar e condicional só aparecem quando a fonte oficial confirma o regime atual.</div>
    <DirtyRecordsGrid />
    <p className="mt-8 text-sm leading-relaxed text-slate-500">Lista inicial com revisão manual. A ausência de um nome não comprova elegibilidade nem inexistência de condenação.</p>
  </main></>;
}
