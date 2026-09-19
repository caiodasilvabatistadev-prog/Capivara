import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import Proposals from "../components/Proposals";
import { person } from "./fixtures";

test("lista propostas com resumo simples, situação e texto oficial", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ title: "Propostas de sua autoria", blocks: [{ kind: "text", text: "Ano 2026. 1 proposta encontrada.", rows: [] }, { kind: "table", text: "", rows: [["Data", "Identificação", "Em palavras simples", "Descrição oficial", "Situação", "Fonte"], ["2026-03-02", "PL 10/2026", "Cria regras sobre atendimento em hospitais.", "Dispõe sobre atendimento em hospitais.", "Aguardando parecer", "https://fonte"]] }] }) }));
  render(<Proposals person={person} initialYear="2026" onLoaded={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Listar propostas de autoria" }));
  expect(await screen.findByRole("heading", { name: "Cria regras sobre atendimento em hospitais." })).toBeVisible();
  expect(screen.getByText("Situação: Aguardando parecer")).toBeVisible();
  await userEvent.click(screen.getByText("Ler descrição original"));
  expect(screen.getByText("Dispõe sobre atendimento em hospitais.")).toBeVisible();
});
