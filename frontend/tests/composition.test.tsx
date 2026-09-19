import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import HouseComposition from "../components/HouseComposition";

const data = {
  provider: "camara",
  house: "Câmara dos Deputados",
  total: 3,
  parties: [{ party: "ABC", seats: 2 }, { party: "XYZ", seats: 1 }],
  source_url: "https://dadosabertos.camara.leg.br/api/v2/deputados",
  fetched_at: "2026-09-19T00:00:00Z",
  notice: "Representação proporcional; não indica posição física.",
};

test("monta pizza, planta proporcional e legenda partidária sob demanda", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => data }));
  render(<HouseComposition />);
  const card = screen.getByRole("heading", { name: "Câmara dos Deputados" }).closest("article")!;
  await userEvent.click(within(card).getByRole("button", { name: "Ver planta e partidos" }));
  expect(await within(card).findByRole("img", { name: /Gráfico de pizza/ })).toBeVisible();
  expect(within(card).getByText("ABC")).toBeVisible();
  expect(within(card).getByText("2")).toBeVisible();
  await userEvent.click(within(card).getByText("Ver também a planta proporcional do plenário"));
  expect(within(card).getByRole("img", { name: /3 cadeiras/ })).toBeVisible();
  expect(card.querySelectorAll("circle")).toHaveLength(3);
});

test("informa quando a composição oficial está indisponível", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  render(<HouseComposition />);
  const card = screen.getByRole("heading", { name: "Senado Federal" }).closest("article")!;
  await userEvent.click(within(card).getByRole("button", { name: "Ver planta e partidos" }));
  expect(await within(card).findByRole("alert")).toHaveTextContent("Não foi possível consultar");
});