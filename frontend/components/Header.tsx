import Brand from "./Brand";

export default function Header({ onNavigate }: { onNavigate: (section: "consulta" | "rankings" | "fontes") => void }) {
  return <header className="site-header">
    <div className="header-inner">
      <button className="brand-home" aria-label="Página inicial — Puxando a Capivara" onClick={() => onNavigate("consulta")}><Brand /></button>
      <nav aria-label="Navegação principal" className="header-nav">
        <button onClick={() => onNavigate("consulta")}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></svg>Consulta</button>
        <button onClick={() => onNavigate("rankings")}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V12M12 20V4M19 20V8" /></svg>Rankings</button>
        <button onClick={() => onNavigate("fontes")}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4v6c0 4-4 7-8 9-4-2-8-5-8-9V7Z" /><path d="m8 12 3 3 5-6" /></svg>Fontes</button>
      </nav>
      <span className="header-status"><span />Dados públicos</span>
    </div>
  </header>;
}
