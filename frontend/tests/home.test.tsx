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
  await user.click(await screen.findByRole("button", { name: "Puxar a capivara de Maria" }));
  await screen.findByText("Dados oficiais consultados na Câmara dos Deputados.");
  return user;
}

test("dashboard mostra gastos e presença sem navegar para a Câmara", async () => {
  const fetch = vi.fn(async (url: string) => ({ ok: true, json: async () => url.endsWith("/news") ? { items: [], notice: "Fixture", fetched_at: "2026-09-18" } : url.includes("/dashboard") ? dashboard : { items: [person], sources: [] } }));
  vi.stubGlobal("fetch", fetch);
  const user = await openDashboard();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(screen.getByText("R$ 500,00")).toBeVisible();
  expect(screen.getByText("10 dias")).toBeVisible();
  expect(screen.getByLabelText("Perfil em leitura: Maria")).toBeVisible();
  expect(fetch).toHaveBeenCalledWith("http://localhost:8000/politicians/camara/1/dashboard", { cache: "no-store" });
  await user.click(screen.getByText("Gastos públicos", { selector: "summary" }));
  expect(screen.getByRole("table")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Voltar aos resultados" }));
  expect(screen.queryByRole("region", { name: "Perfil" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Puxar a capivara de Maria" })).toBeVisible();
});

test.each([true, false])("download do PDF ou erro (%s)", async ok => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url.endsWith("/reports/pdf") ? { ok, blob: async () => new Blob(["%PDF-"]) } : { ok: true, json: async () => url.endsWith("/news") ? { items: [], notice: "Fixture", fetched_at: "2026-09-18" } : url.includes("/dashboard") ? dashboard : { items: [person], sources: [] } }));
  const create = vi.fn(() => "blob:report"); const revoke = vi.fn();
  vi.stubGlobal("URL", class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  const user = await openDashboard();
  await user.click(screen.getByRole("button", { name: "Baixar PDF completo" }));
  if (ok) { expect(click).toHaveBeenCalledOnce(); expect(revoke).toHaveBeenCalledWith("blob:report"); }
  else expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível gerar o PDF");
});

test.each([true, false])("mostra vazio ou erro (%s)", async ok => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, json: async () => ({ items: [], sources: [] }) }));
  render(<Home />); const user = userEvent.setup();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria"); await user.click(screen.getByRole("button", { name: "Buscar" }));
  if (ok) expect(await screen.findByText("Nenhuma pessoa encontrada nas fontes disponíveis. Isso não significa ausência de candidatura ou cargo.")).toBeVisible();
  else expect(await screen.findByRole("alert")).toBeVisible();
});

test("busca única mostra cargos e poderes e informa fontes indisponíveis", async () => {
  const people = [
    { ...person, id: 1, provider: "governadores", name: "Maria Governo", institution: "Governo SP", role: "Governadora", party: "ABC", power: "executivo" },
    { ...person, id: 2, provider: "judiciario", name: "Maria Tribunal", institution: "STJ", role: "Ministra", party: "Não se aplica", power: "judiciario" },
  ];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: people, sources: [{provider: "tse2026", name: "Candidaturas TSE 2026", available: false, matches: 0}] }) }));
  render(<Home />);
  const user = userEvent.setup();
  expect(screen.queryByRole("combobox", { name: "Casa legislativa" })).not.toBeInTheDocument();
  expect(screen.queryByRole("combobox", { name: "Órgão" })).not.toBeInTheDocument();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria");
  expect(await screen.findByRole("option", { name: /Maria Governo/ })).toHaveTextContent("Governadora · ABC · Executivo");
  expect(screen.getByRole("option", { name: /Maria Tribunal/ })).toHaveTextContent("Ministra · Não se aplica · Judiciário");
  expect(screen.getByText("Consulta parcial — algumas fontes indisponíveis")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Buscar" }));
  expect(await screen.findByRole("heading", { name: "Maria Governo" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Maria Tribunal" })).toBeVisible();
});

test("não mostra votação parlamentar em perfil do Executivo", async () => {
  const executive = { ...person, provider: "presidentes", name: "Maria Executiva", role: "Presidente da República", institution: "Presidência da República", power: "executivo" };
  const executiveDashboard = { ...dashboard, politician: executive };
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ ok: true, json: async () => url.endsWith("/news") ? { items: [], notice: "Fixture", fetched_at: "2026-09-18" } : url.includes("/dashboard") ? executiveDashboard : { items: [executive], sources: [] } })));
  render(<Home />);
  const user = userEvent.setup();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria");
  await user.click(screen.getByRole("button", { name: "Buscar" }));
  await user.click(await screen.findByRole("button", { name: "Puxar a capivara de Maria Executiva" }));
  expect(await screen.findByRole("heading", { name: "Maria Executiva" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Como votou nos assuntos da população?" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Como votou/ })).not.toBeInTheDocument();
});

