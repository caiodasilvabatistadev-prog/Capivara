import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import Rankings, { type Ranking } from "../components/Rankings";
import Home from "../app/page";

const base: Ranking = { provider: "camara", metric: "expenses", year: 2026, status: "ready", title: "Gastos", unit: "BRL", notice: "Somente cota, sem avaliação política.", source_url: "https://example.com/fonte", source_as_of: null, fetched_at: "2026-09-18T00:00:00Z", covered: 2, total: null, entries: [{ position: 1, id: 1, name: "Maria", value: "1234.56", detail: "Registro oficial" }] };
function expenses() { return screen.getByRole("heading", { name: "Maiores gastos com cota parlamentar" }).closest("article")!; }

test("comparação consulta fonte sob demanda e abre dashboard interno", async () => {
  const onOpen = vi.fn();
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => base });
  vi.stubGlobal("fetch", fetch);
  render(<Rankings provider="camara" onOpen={onOpen} />);
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(within(expenses()).getByRole("button", { name: "Consultar comparação" }));
  expect(await screen.findByText(/1.234,56/)).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Ver dashboard de Maria" }));
  expect(onOpen).toHaveBeenCalledWith("camara", 1);
  expect(fetch.mock.calls[0][0]).toContain("metric=expenses");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

test("poder e ano limpam listas anteriores e preservam fundos como nacionais", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => base }));
  render(<Home />);
  await userEvent.click(within(expenses()).getByRole("button", { name: "Consultar comparação" }));
  expect(await screen.findByText("Maria")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Judiciário" }));
  expect(screen.queryByText("Maria")).not.toBeInTheDocument();
  expect(screen.getByText("Recursos dos partidos — âmbito nacional")).toBeVisible();
  await userEvent.click(within(expenses()).getByRole("button", { name: "Consultar comparação" }));
  expect(await screen.findByText("Maria")).toBeVisible();
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Ano da atuação" }), String(new Date().getFullYear() - 1));
  expect(screen.queryByText("Maria")).not.toBeInTheDocument();
});

test("dados parciais e indisponíveis nunca viram ranking completo", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...base, status: "partial", covered: 1, total: 3 }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...base, status: "unavailable", entries: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...base, status: "not_applicable", entries: [] }) })
    .mockResolvedValueOnce({ ok: false }));
  render(<Rankings provider="camara" onOpen={() => {}} />);
  await userEvent.click(within(expenses()).getByRole("button", { name: "Consultar comparação" }));
  expect(await screen.findByText(/Cobertura parcial: 1 de 3/)).toBeVisible();
  await userEvent.click(within(expenses()).getByRole("button", { name: "Atualizar comparação" }));
  expect(await screen.findByText("Dados ainda não disponíveis para esta comparação")).toBeVisible();
  expect(screen.queryByText("Maria")).not.toBeInTheDocument();
  await userEvent.click(within(expenses()).getByRole("button", { name: "Atualizar comparação" }));
  expect(await screen.findByText("Indicador parlamentar não aplicável a este poder")).toBeVisible();
  await userEvent.click(within(expenses()).getByRole("button", { name: "Atualizar comparação" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível consultar esta fonte");
});
