import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import Home from "../app/page";
import { person, dashboard } from "./fixtures";

async function openDashboard() {
  render(<Home />); const user = userEvent.setup();
  expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria");
  await user.click(screen.getByRole("button", { name: "Buscar" }));
  await user.click(await screen.findByRole("button", { name: "Ver dashboard de Maria" }));
  await screen.findByText("Dados oficiais consultados na Câmara dos Deputados.");
  return user;
}

test("dashboard mostra gastos e presença sem navegar para a Câmara", async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [person] }).mockResolvedValueOnce({ ok: true, json: async () => dashboard });
  vi.stubGlobal("fetch", fetch);
  const user = await openDashboard();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(screen.getByText("R$ 500,00")).toBeVisible();
  expect(screen.getByText("10 dias")).toBeVisible();
  expect(fetch).toHaveBeenLastCalledWith("http://localhost:8000/politicians/camara/1/dashboard", { cache: "no-store" });
  await user.click(screen.getByText("Gastos públicos", { selector: "summary" }));
  expect(screen.getByRole("table")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Voltar aos resultados" }));
  expect(screen.queryByRole("region", { name: "Perfil" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Ver dashboard de Maria" })).toBeVisible();
});

test.each([true, false])("download do PDF ou erro (%s)", async ok => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [person] }).mockResolvedValueOnce({ ok: true, json: async () => dashboard }).mockResolvedValueOnce({ ok, blob: async () => new Blob(["%PDF-"]) }));
  const create = vi.fn(() => "blob:report"); const revoke = vi.fn();
  vi.stubGlobal("URL", class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  const user = await openDashboard();
  await user.click(screen.getByRole("button", { name: "Baixar PDF completo" }));
  if (ok) { expect(click).toHaveBeenCalledOnce(); expect(revoke).toHaveBeenCalledWith("blob:report"); }
  else expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível gerar o PDF");
});

test.each([true, false])("mostra vazio ou erro (%s)", async ok => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, json: async () => [] }));
  render(<Home />); const user = userEvent.setup();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria"); await user.click(screen.getByRole("button", { name: "Buscar" }));
  if (ok) expect(await screen.findByText("Nenhuma pessoa encontrada nesta fonte.")).toBeVisible();
  else expect(await screen.findByRole("alert")).toBeVisible();
});
