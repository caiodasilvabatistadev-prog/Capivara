import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Biography from "../components/Biography";
import { person } from "./fixtures";

test("mostra biografia complementar com aviso e fonte dentro do projeto", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      found: true,
      title: "Maria",
      description: "política brasileira",
      extract: "Maria iniciou sua trajetória na política municipal.",
      source_url: "https://pt.wikipedia.org/wiki/Maria",
      fetched_at: "2026-09-19T00:00:00Z",
      notice: "Conteúdo comunitário.",
      media: [{ title: "Maria apresenta projeto", publisher: "G1", published_at: "2026-09-18T00:00:00Z", source_url: "https://g1.globo.com", reference_url: "https://news.google.com/a" }],
    }),
  }));
  render(<Biography person={{ ...person, photo_url: "https://example.com/maria.jpg" }} />);
  expect(await screen.findByText(/iniciou sua trajetória/)).toHaveClass("text-slate-100");
  expect(screen.getByText("Conteúdo comunitário.")).toBeVisible();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(screen.getByAltText("Foto de Maria")).toBeInTheDocument();
  expect(screen.getByText("Maria apresenta projeto")).toBeVisible();
});

test("não atribui artigo de homônimo e informa falha", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ found: false, media: [] }) })
    .mockResolvedValueOnce({ ok: false });
  vi.stubGlobal("fetch", fetch);
  const { rerender } = render(<Biography person={person} />);
  expect(await screen.findByText(/título exatamente igual/)).toBeVisible();
  rerender(<Biography person={{ ...person, id: 2 }} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("indisponível");
});
