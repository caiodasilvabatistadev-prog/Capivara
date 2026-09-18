import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import Home from "../app/page";
const person = { id: 1, provider: "camara", name: "Maria", party: "ABC", state: "SP", email: null, source_url: "https://www.camara.leg.br/deputados/1" };
test("busca e abre perfil com fonte", async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [person] }).mockResolvedValueOnce({ ok: true, json: async () => person });
  vi.stubGlobal("fetch", fetch);
  render(<Home />); const user = userEvent.setup();
  expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
  await user.type(screen.getByRole("textbox"), "Maria");
  await user.click(screen.getByRole("button", { name: "Buscar" }));
  await user.click(await screen.findByRole("button", { name: "Ver perfil de Maria" }));
  expect(await screen.findByRole("link", { name: "Consultar fonte oficial" })).toHaveAttribute("href", person.source_url);
  expect(fetch).toHaveBeenLastCalledWith("http://localhost:8000/politicians/camara/1", { cache: "no-store" });
});
test.each([true, false])("mostra vazio ou erro (%s)", async ok => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, json: async () => [] }));
  render(<Home />); const user = userEvent.setup();
  await user.type(screen.getByRole("textbox"), "Maria"); await user.click(screen.getByRole("button", { name: "Buscar" }));
  if (ok) expect(await screen.findByText("Nenhum parlamentar encontrado.")).toBeVisible();
  else expect(await screen.findByRole("alert")).toBeVisible();
});
