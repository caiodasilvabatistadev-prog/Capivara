import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Career from "../components/Career";
import { person } from "./fixtures";

test("mostra profissão e cargos anteriores oficiais", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ available: true, professions: [{ title: "Professora" }], previous_offices: [{ title: "Vereadora", detail: "Cidade · SP", period: "2000–2004" }], notice: "Fonte oficial." }) }));
  render(<Career person={person} />);
  expect(await screen.findByText("Professora")).toBeVisible();
  expect(screen.getByText("Vereadora")).toBeVisible();
  expect(screen.getByText(/Cidade · SP/)).toBeVisible();
});

test("explica lacuna e erro de consulta", async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ available: false, notice: "Fonte ainda não publica." }) }).mockResolvedValueOnce({ ok: false });
  vi.stubGlobal("fetch", fetch);
  const { rerender } = render(<Career person={person} />);
  expect(await screen.findByText("Fonte ainda não publica.")).toBeVisible();
  rerender(<Career person={{ ...person, id: 2 }} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("indisponível");
});

test("identifica e liga a fonte complementar Wikimedia", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ available: true, professions: [{ title: "Metalúrgico" }], previous_offices: [{ title: "Presidente do Brasil" }], notice: "Informações complementares.", source_kind: "complementary", source_name: "Wikidata e Wikipédia", source_url: "https://pt.wikipedia.org/wiki/Lula" }) }));
  render(<Career person={{ ...person, provider: "presidentes" }} />);
  expect(await screen.findByText("Profissões registradas")).toBeVisible();
  expect(screen.getByText("Cargos públicos registrados")).toBeVisible();
  expect(screen.getByRole("link", { name: "Ver Wikidata e Wikipédia" })).toHaveAttribute("href", "https://pt.wikipedia.org/wiki/Lula");
});
