import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import PublicContext, { contextBlocks, type Context } from "../components/PublicContext";
import { person } from "./fixtures";

const source = { publisher: "Fonte de teste", url: "https://example.com/fonte", published_at: "2024-05-21" };
const base: Context = { subject_name: "Maria", reviewed_at: "2026-09-18", notice: "Cobertura parcial, com datas históricas.", actions: [], cases: [] };

test("sem curadoria não afirma ausência de processos", async () => {
  const loaded = vi.fn();
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ ...base, reviewed_at: null }) })));
  render(<PublicContext person={person} onLoaded={loaded} />);
  await userEvent.click(screen.getByRole("button", { name: "Consultar notícias e registros revisados" }));
  expect(await screen.findByText(/Isso não significa ausência de processos/)).toBeVisible();
  expect(screen.getByText(/Não realizada para este perfil/)).toBeVisible();
  expect(loaded).toHaveBeenCalledOnce();
});

test("cada caso preserva estado, natureza, data e fontes, inclusive na exportação", async () => {
  const statuses: Context["cases"][number]["status"][] = ["condenacao_definitiva", "condenacao_recorrivel", "em_andamento", "absolvido", "arquivado", "anulado", "pedido_rejeitado"];
  const data: Context = { ...base, cases: statuses.map((status, i) => ({ title: "Caso de teste " + i, summary: "Resumo do registro", category: "eleitoral", status, court: "TSE", case_number: "Processo " + i, status_as_of: "2024-05-21", final_judgment: status === "condenacao_definitiva", official_source: source, journalism: source })), actions: [{ title: "Ação de teste", summary: "Benefício previsto, sem execução comprovada", attribution: "Autoria compartilhada", stage: "proposta", stage_as_of: "2025-10-30", official_source: source, journalism: source }] };
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => data })));
  render(<PublicContext person={person} onLoaded={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "Consultar notícias e registros revisados" }));
  expect(await screen.findByText("Absolvido neste processo")).toBeVisible();
  expect(screen.getByText("Processo em andamento — sem condenação registrada nesta revisão")).toBeVisible();
  expect(screen.getByText("Condenação com possibilidade de recurso — não definitiva")).toBeVisible();
  expect(screen.getByText("Pedido rejeitado / ação improcedente")).toBeVisible();
  expect(screen.getByText(/Proposta · 30\/10\/2025/)).toBeVisible();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(JSON.stringify(contextBlocks(data))).toContain("https://example.com/fonte");
  expect(JSON.stringify(contextBlocks(data))).toContain("Estado na data: 21/05/2024");
  expect(JSON.stringify(contextBlocks({ ...base, reviewed_at: null }))).toContain("Não realizada");
});

test("falha de consulta permite tentar novamente sem inventar registros", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false })));
  render(<PublicContext person={person} onLoaded={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "Consultar notícias e registros revisados" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível consultar");
  expect(screen.getByRole("button", { name: "Consultar notícias e registros revisados" })).toBeEnabled();
});
