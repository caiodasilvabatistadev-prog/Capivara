import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, expect, vi } from "vitest";
import ParliamentRecords from "../components/ParliamentRecords";
import { person } from "./fixtures";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
test("carrega destinos e votos, preserva etapa e filtra assuntos", async () => {
  const onLoaded = vi.fn();
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ ok: true, json: async () => url.includes("amendments") ? { title: "Destinos das emendas", blocks: [{ kind: "table", text: "", rows: [["Modalidade", "Destino publicado", "Finalidade publicada", "Previsto ou autorizado", "Empenhado", "Pago", "Situação"], ["Emenda Pix · Transferência especial", "Fundo de Saúde", "Hospital no Ceará", "R$ 10,00", "R$ 5,00", "R$ 0,00", "CIENTE"]] }] } : { title: "Votos e assuntos em Plenário", blocks: [{ kind: "text", text: "Sem registro não significa falta", rows: [] }, { kind: "table", text: "", rows: [["Data", "Objeto", "Contexto", "Voto", "Fonte"], ["2026-09-01", "Emenda sobre saúde", "Hospital público", "Não", "https://dadosabertos.camara.leg.br/a"], ["2026-09-01", "Requerimento sobre impostos", "Tributo", "Sem voto nominal registrado", "https://dadosabertos.camara.leg.br/b"]] }] } })));
  render(<ParliamentRecords person={person} onLoaded={onLoaded} />);
  const user=userEvent.setup();
  expect(screen.getByText("O que é Emenda Pix?")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Consultar emendas e Emendas Pix" }));
  expect(await screen.findByText("Hospital no Ceará")).toBeVisible();
  expect(screen.getByText("R$ 0,00")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Consultar votos individuais" }));
  expect(await screen.findByText("Como votou: Não — contra o objeto votado")).toBeVisible();
  expect(screen.queryByText(/Como votou: Sem voto nominal registrado/)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Saúde" }));
  expect(screen.queryByText("Requerimento sobre impostos")).toBeNull();
  expect(onLoaded).toHaveBeenCalledTimes(2);
});

test("destaca o assunto popular antes do voto sem ocultar o texto oficial", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ title: "Votos e assuntos em Plenário", blocks: [{ kind: "table", text: "", rows: [["Data", "Objeto", "Contexto", "Voto", "Fonte"], ["2026-09-01", "Projeto que regulamenta a cannabis", "Debate sobre legalização da maconha", "Sim", "https://fonte"]] }] }) }));
  render(<ParliamentRecords person={person} show="votes" onLoaded={() => undefined} />);
  await userEvent.click(screen.getByRole("button", { name: "Consultar votos individuais" }));
  expect(await screen.findByRole("heading", { name: "Legalização ou regulamentação da maconha" })).toBeVisible();
  expect(screen.getByText("Como votou: Sim — a favor do objeto votado")).toBeVisible();
  expect(screen.getByText(/Texto original: Projeto que regulamenta/)).toBeVisible();
});
test("limites de cobertura e falhas ficam visíveis", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  const { rerender }=render(<ParliamentRecords person={{ ...person, provider: "senado" }} onLoaded={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Consultar emendas e Emendas Pix" }));
  expect(await screen.findByRole("alert")).toBeVisible();
  rerender(<ParliamentRecords person={{ ...person, provider: "executivo" }} onLoaded={vi.fn()} />);
  expect(screen.getAllByText(/não se aplicam a este cargo/)).toHaveLength(2);
});

