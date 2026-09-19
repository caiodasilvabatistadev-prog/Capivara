"use client";
import { useEffect, useRef, useState } from "react";

export default function Share() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [local, setLocal] = useState(true);
  const [status, setStatus] = useState("");
  const [fallback, setFallback] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const text = "Saiba todos os passos do seu candidato — Puxando a Capivara.";
  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    function escape(event: KeyboardEvent) { if (event.key === "Escape") { setOpen(false); trigger.current?.focus(); } }
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", dismiss); document.removeEventListener("keydown", escape); };
  }, [open]);
  function toggle() {
    const address = window.location.origin;
    setUrl(address);
    setLocal(["localhost", "127.0.0.1", "0.0.0.0", "[::1]"].includes(window.location.hostname));
    setStatus(""); setFallback(false); setOpen(!open);
  }
  async function instagram() {
    try {
      if (navigator.share) {
        await navigator.share({ title: "Puxando a Capivara", text, url });
        setStatus("Compartilhamento encaminhado pelo dispositivo.");
      } else {
        await navigator.clipboard.writeText(`${text} ${url}`);
        setStatus("Texto e link copiados. Cole no Instagram para compartilhar.");
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      setFallback(true); setStatus("Copie o texto abaixo para compartilhar.");
    }
  }
  return <div ref={root} className="share-menu">
    <button ref={trigger} className="share-toggle" aria-label="Compartilhar site" aria-expanded={open} aria-controls={open ? "share-panel" : undefined} onClick={toggle}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="12" r="3" /><circle cx="18" cy="5" r="3" /><circle cx="18" cy="19" r="3" /><path d="m9 10 6-4M9 14l6 4" /></svg><span>Compartilhar</span></button>
    {open && <div id="share-panel" className="share-panel" role="region" aria-label="Opções de compartilhamento">
      <p>{local ? "Endereço local: o compartilhamento público estará disponível após a publicação do site." : "Compartilhe o projeto. No dispositivo, escolha Instagram se essa opção estiver disponível."}</p>
      <button disabled={local} onClick={() => window.open("https://wa.me/?text=" + encodeURIComponent(`${text} ${url}`), "_blank", "noopener,noreferrer")}>WhatsApp</button>
      <button disabled={local} onClick={() => window.open("https://x.com/intent/tweet?" + new URLSearchParams({ text, url }), "_blank", "noopener,noreferrer")}>X</button>
      <button disabled={local} onClick={() => void instagram()}>Instagram</button>
      {status && <p role="status">{status}</p>}
      {fallback && <textarea readOnly aria-label="Texto para compartilhar" value={`${text} ${url}`} onFocus={event => event.target.select()} />}
    </div>}
  </div>;
}
