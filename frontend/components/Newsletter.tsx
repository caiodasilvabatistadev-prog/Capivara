"use client";
import { useState } from "react";
import { type Politician, post } from "../lib/api";

type Result = { message: string; confirmation_required: boolean };

export default function Newsletter({ person }: { person?: Politician }) {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(""); setError("");
    try {
      const result = await post<Result>("/subscriptions", {
        email, consent,
        politician_provider: person?.provider || null,
        politician_id: person?.id || null,
        politician_name: person?.name || null,
      });
      setMessage(result.message); setEmail(""); setConsent(false);
    } catch (caught) { setError((caught as Error).message); }
    finally { setBusy(false); }
  }
  const title = person ? `Receba alertas sobre ${person.name}` : "Receba atualizações por e-mail";
  return <section aria-label="Atualizações por e-mail" className="mt-12 rounded-2xl border bg-white p-6">
    <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">{person ? "Acompanhar esta pessoa" : "Acompanhe o projeto"}</p>
    <h2 className="mt-2 text-2xl font-bold">{title}</h2>
    <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600">{person ? "Avisaremos quando houver novas informações públicas verificadas neste perfil." : "Receba novidades do projeto. Não é necessário criar uma conta."}</p>
    <form className="mt-5 max-w-xl space-y-3" onSubmit={submit}>
      <label className="block text-sm font-semibold" htmlFor={person ? "candidate-alert-email" : "newsletter-email"}>Seu e-mail</label>
      <div className="flex flex-col gap-3 sm:flex-row"><input id={person ? "candidate-alert-email" : "newsletter-email"} type="email" required autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="voce@exemplo.com" className="min-w-0 flex-1 rounded-xl border bg-white p-4 text-slate-950" /><button type="submit" disabled={busy || !consent} className="rounded-xl bg-emerald-900 px-5 py-4 font-semibold text-white disabled:opacity-60">{busy ? "Enviando…" : person ? "Criar alerta" : "Quero receber"}</button></div>
      <label className="flex items-start gap-3 text-xs leading-relaxed text-slate-600"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} className="mt-1" />Autorizo o envio de e-mails e posso cancelar a inscrição a qualquer momento.</label>
    </form>
    {message && <p role="status" className="mt-4 text-sm font-medium text-emerald-800">{message}</p>}
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
  </section>;
}
