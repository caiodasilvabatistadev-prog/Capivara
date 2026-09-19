"use client";
import { useEffect, useState } from "react";
import Header from "../../components/Header";
import { request } from "../../lib/api";

export default function ConfirmSubscription() {
  const [message, setMessage] = useState("Confirmando sua inscrição…");
  const [error, setError] = useState(false);
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token") || "";
    request<{ message: string }>("/subscriptions/confirm/" + encodeURIComponent(token))
      .then(result => setMessage(result.message))
      .catch(() => { setError(true); setMessage("O link de confirmação é inválido ou expirou."); });
  }, []);
  return <><Header /><main className="mx-auto max-w-3xl px-5 py-20"><section className="rounded-2xl border bg-white p-8"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Alertas por e-mail</p><h1 className="mt-3 text-3xl font-bold">Confirmação da inscrição</h1><p role={error ? "alert" : "status"} className="mt-5 text-slate-600">{message}</p></section></main></>;
}
