"use client";
import { useRouter } from "next/navigation";
import Share from "./Share";
import Brand from "./Brand";

export default function Header({ onNavigate }: { onNavigate?: (section: "consulta" | "fontes") => void }) {
  const router = useRouter();
  return <header className="site-header">
    <div className="header-inner">
      <button className="brand-home" aria-label="Página inicial — Puxando a Capivara" onClick={() => router.push("/")}><Brand /></button>
      <nav aria-label="Navegação principal" className="header-nav">
        <button onClick={() => onNavigate ? onNavigate("consulta") : router.push("/#public-search")}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></svg>Consulta</button>
        <button onClick={() => router.push("/rankings")}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V12M12 20V4M19 20V8" /></svg>Rankings</button>
        <button onClick={() => router.push("/familias")}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="6" r="3" /><circle cx="5" cy="18" r="3" /><circle cx="19" cy="18" r="3" /><path d="M12 9v4M5 15v-2h14v2" /></svg>Famílias</button>
        <button onClick={() => router.push("/fichas-sujas")}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 3 7v5c0 5 3.5 8 9 10 5.5-2 9-5 9-10V7Z" /><path d="m9 9 6 6M15 9l-6 6" /></svg>Fichas sujas</button>
        <button onClick={() => router.push("/como-funciona")}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3Z" /></svg>Como funciona</button>
        <button onClick={() => router.push("/fontes")}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4v6c0 4-4 7-8 9-4-2-8-5-8-9V7Z" /><path d="m8 12 3 3 5-6" /></svg>Fontes</button>
      </nav>
      <Share /><span className="header-status"><span />Dados públicos</span>
    </div>
  </header>;
}
