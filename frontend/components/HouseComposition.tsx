"use client";
import { useState } from "react";
import { request } from "../lib/api";

type Composition = {
  provider: "camara" | "senado";
  house: string;
  total: number;
  parties: { party: string; seats: number }[];
  source_url: string;
  fetched_at: string;
  notice: string;
};

const colors = ["#34d399", "#60a5fa", "#f59e0b", "#f472b6", "#a78bfa", "#22d3ee", "#fb7185", "#a3e635", "#f97316", "#818cf8", "#2dd4bf", "#e879f9", "#facc15", "#94a3b8", "#4ade80", "#38bdf8", "#c084fc", "#fda4af"];

function points(total: number, rows: number) {
  const activeRows = Math.min(rows, total);
  const capacities = Array.from({ length: activeRows }, (_, row) => Math.max(5, Math.round((70 + row * 19) * Math.PI / 12)));
  const scale = total / capacities.reduce((sum, value) => sum + value, 0);
  const allocated = capacities.map(value => Math.max(1, Math.floor(value * scale)));
  while (allocated.reduce((sum, value) => sum + value, 0) < total) allocated[allocated.length - 1]++;
  while (allocated.reduce((sum, value) => sum + value, 0) > total) {
    const index = allocated.findLastIndex(value => value > 1);
    allocated[index]--;
  }
  return allocated.flatMap((count, row) => Array.from({ length: count }, (_, seat) => {
    const angle = Math.PI + (Math.PI * (seat + 0.5) / count);
    const radius = 67 + row * (205 / Math.max(1, activeRows - 1));
    return { x: 300 + Math.cos(angle) * radius, y: 292 + Math.sin(angle) * radius };
  }));
}

function Chamber({ data }: { data: Composition }) {
  const seats = data.parties.flatMap((party, partyIndex) => Array.from({ length: party.seats }, () => ({ ...party, color: colors[partyIndex % colors.length] })));
  const layout = points(data.total, data.provider === "camara" ? 14 : 7);
  return <svg viewBox="0 0 600 330" role="img" aria-label={`Planta proporcional de ${data.house}: ${data.total} cadeiras distribuídas por partido`} className="w-full">
    <path d="M55 294 A245 245 0 0 1 545 294" fill="none" stroke="currentColor" strokeOpacity=".12" strokeWidth="2" />
    {seats.map((seat, index) => <circle key={index} cx={layout[index].x} cy={layout[index].y} r={data.provider === "camara" ? 4.2 : 7.2} fill={seat.color}><title>{seat.party} · 1 cadeira</title></circle>)}
    <path d="M260 287h80v28h-80z" rx="8" fill="currentColor" opacity=".12" />
    <text x="300" y="305" textAnchor="middle" className="fill-current text-[11px] font-semibold">Mesa</text>
  </svg>;
}

function Pie({ data }: { data: Composition }) {
  const slices = data.parties.map((party, index) => {
    const start = data.parties.slice(0, index).reduce((sum, item) => sum + item.seats, 0) / data.total * 100;
    const end = start + party.seats / data.total * 100;
    return `${colors[index % colors.length]} ${start}% ${end}%`;
  });
  return <div className="mx-auto my-7 grid max-w-xl items-center gap-7 sm:grid-cols-[minmax(180px,260px)_1fr]">
    <div role="img" aria-label={`Gráfico de pizza da composição de ${data.house} por partido`} className="relative aspect-square rounded-full" style={{ background: `conic-gradient(${slices.join(",")})` }}>
      <div className="absolute inset-[28%] flex items-center justify-center rounded-full bg-white text-center"><span><strong className="block text-2xl">{data.total}</strong><span className="text-xs text-slate-500">cadeiras</span></span></div>
    </div>
    <p className="text-sm leading-relaxed text-slate-600">O tamanho de cada fatia representa a quantidade de parlamentares do partido em exercício.</p>
  </div>;
}

function House({ provider }: { provider: "camara" | "senado" }) {
  const [data, setData] = useState<Composition | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load() {
    setBusy(true); setError("");
    try { setData(await request<Composition>(`/composition/${provider}`)); }
    catch { setError("Não foi possível consultar a composição oficial agora."); }
    finally { setBusy(false); }
  }
  const label = provider === "camara" ? "Câmara dos Deputados" : "Senado Federal";
  return <article className="rounded-2xl border bg-white p-5">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Composição em exercício</p>
    <h3 className="mt-2 text-xl font-bold">{label}</h3>
    {!data && <button className="mt-4 rounded-xl border px-4 py-3 text-sm font-semibold" disabled={busy} onClick={() => void load()}>{busy ? "Montando o plenário…" : "Ver planta e partidos"}</button>}
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    {data && <><Pie data={data} /><p className="mb-4 text-center text-sm font-bold">{data.total} parlamentares em exercício</p><ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">{data.parties.map((party, index) => <li className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm" key={party.party}><span className="flex min-w-0 items-center gap-2"><span className="h-3 w-3 shrink-0 rounded-full" style={{ background: colors[index % colors.length] }} /><span className="truncate font-semibold">{party.party}</span></span><strong>{party.seats}</strong></li>)}</ul><details className="mt-5"><summary className="cursor-pointer text-sm font-semibold">Ver também a planta proporcional do plenário</summary><Chamber data={data} /></details><p className="mt-4 text-xs leading-relaxed text-slate-500">{data.notice} Consulta em {new Date(data.fetched_at).toLocaleString("pt-BR")}.</p><details className="mt-3 text-xs text-slate-500"><summary className="cursor-pointer font-semibold">Fonte oficial</summary><p className="mt-2 break-all">{data.source_url}</p></details></>}
  </article>;
}

export default function HouseComposition() {
  return <section aria-label="Composição partidária das casas legislativas" className="mt-10">
    <p className="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-800">Composição partidária atual</p>
    <h2 className="text-2xl font-bold">Quantas cadeiras cada partido ocupa?</h2>
    <p className="mb-5 mt-3 text-sm leading-relaxed text-slate-500">Os gráficos de pizza comparam a participação de cada partido. As cores servem para leitura; não representam ideologia, governo ou oposição.</p>
    <div className="grid items-start gap-5 lg:grid-cols-2"><House provider="camara" /><House provider="senado" /></div>
  </section>;
}
