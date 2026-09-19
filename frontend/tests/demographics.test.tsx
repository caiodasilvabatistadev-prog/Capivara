import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Demographics from "../components/Demographics";

const snapshot = { year: 2024, scope: "Candidaturas registradas", total: 100, sex_total: 100, race_total: 100, sex: [{ label: "Feminino", value: 40, percentage: 40 }, { label: "Masculino", value: 60, percentage: 60 }], race: [{ label: "Parda", value: 55, percentage: 55 }, { label: "Branca", value: 45, percentage: 45 }], source_url: "https://dadosabertos.tse.jus.br/", notice: "Dados autodeclarados; não representam mandatos." };

test("mostra sexo e raça/cor autodeclarados com fonte e período", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => snapshot });
  vi.stubGlobal("fetch", fetch); render(<Demographics />);
  expect(await screen.findByRole("heading", { name: "Sexo autodeclarado" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Raça/cor autodeclarada" })).toBeVisible();
  expect(screen.getByText("40 %")).toBeVisible();
  expect(screen.getByRole("link", { name: /Publicação oficial do TSE/ })).toHaveAttribute("href", snapshot.source_url);
  expect(fetch).toHaveBeenCalledWith("http://localhost:8000/demographics?year=2024", expect.anything());
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});

test("informa indisponibilidade sem inventar números", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false })); render(<Demographics />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível consultar");
});
