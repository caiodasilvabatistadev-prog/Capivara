import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import News from "../components/News";
const person = { id: 1, provider: "camara", name: "Maria", party: "X", state: "SP", email: null, photo_url: null, source_url: "https://example.com" };
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
test("busca ao abrir o perfil e mostra título sem confirmar situação judicial", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ subject_name: "Maria", notice: "Busca parcial", fetched_at: "2026-09-18T12:00:00Z", items: [{ title: "Maria investigada", publisher: "G1", published_at: "2024-05-21T12:00:00Z", source_url: "https://g1.globo.com", reference_url: "https://news.google.com/a", matched_terms: ["investigação"] }] }) });
  vi.stubGlobal("fetch", fetch); render(<News person={person} />);
  expect(await screen.findByText("Maria investigada")).toBeInTheDocument();
  expect(screen.getByText(/Situação judicial não verificada/)).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
  expect(fetch.mock.calls[0][0]).toContain("/politicians/camara/1/news");
});
test("falha pode ser repetida e resultado vazio não certifica ausência de processos", async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ ok: true, json: async () => ({ items: [], notice: "Não confirma ausência de processos", fetched_at: "2026-09-18T12:00:00Z" }) });
  vi.stubGlobal("fetch", fetch); render(<News person={person} />);
  await screen.findByRole("alert"); await userEvent.click(screen.getByRole("button", { name: "Buscar novamente" }));
  await waitFor(() => expect(screen.getByText(/Nenhum título encontrado/)).toBeInTheDocument());
});
