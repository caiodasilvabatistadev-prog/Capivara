import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import PoliticalFamily from "../components/PoliticalFamily";
import { person } from "./fixtures";

test("mostra somente parentescos documentados e a prova", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ found: true, members: [{ name: "João", relationship: "pai", description: "político brasileiro", evidence_url: "https://www.wikidata.org/wiki/Q1", political_profile: true }], notice: "Cobertura parcial." }) }));
  render(<PoliticalFamily person={person} />);
  expect(await screen.findByText("João")).toBeVisible();
  expect(screen.getByText("político brasileiro")).toBeVisible();
  expect(screen.getByRole("link", { name: /documento/ })).toHaveAttribute("href", "https://www.wikidata.org/wiki/Q1");
  expect(screen.getByRole("link", { name: "Puxar a capivara de João" })).toHaveAttribute("href", "/?q=Jo%C3%A3o#public-search");
  expect(screen.getByText("Cobertura parcial.")).toBeVisible();
});

test("explica resultado vazio e indisponibilidade", async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ found: false, notice: "Parcial" }) }).mockResolvedValueOnce({ ok: false });
  vi.stubGlobal("fetch", fetch);
  const { rerender } = render(<PoliticalFamily person={person} />);
  expect(await screen.findByText(/não comprova ausência/)).toBeVisible();
  rerender(<PoliticalFamily person={{ ...person, id: 2 }} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("indisponíveis");
});
