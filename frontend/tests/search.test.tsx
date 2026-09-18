import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import Home from "../app/page";
import { dashboard, person } from "./fixtures";

const response = (value: unknown) => ({ ok: true, json: async () => value });

test("sugestões aceitam teclado e abrem perfil sem sair do projeto", async () => {
  const fetch = vi.fn(async (url: string) => response(url.includes("/autocomplete") ? [person] : dashboard));
  vi.stubGlobal("fetch", fetch);
  render(<Home />); const user = userEvent.setup();
  const input = screen.getByRole("combobox", { name: "Nome da pessoa" });
  await user.type(input, "Ma");
  await screen.findByRole("option", { name: /Maria/ });
  expect(input).toHaveAttribute("aria-expanded", "true");
  await user.keyboard("{ArrowDown}");
  expect(screen.getByRole("option", { name: /Maria/ })).toHaveAttribute("aria-selected", "true");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  await user.type(input, "r"); await screen.findByRole("option", { name: /Maria/ });
  await user.keyboard("{ArrowUp}{Enter}");
  await screen.findByRole("region", { name: "Perfil" });
  expect(fetch.mock.calls.at(-1)?.[0]).toContain("/politicians/camara/1/dashboard");
  await user.click(screen.getByRole("button", { name: "Voltar aos resultados" }));
  expect(screen.getByRole("button", { name: "Ver dashboard de Maria" })).toBeVisible();
});

test("resposta antiga não substitui sugestões de uma busca nova", async () => {
  let resolveOld!: (value: ReturnType<typeof response>) => void;
  const fetch = vi.fn((url: string) => url.includes("q=Ma&") || url.endsWith("q=Ma")
    ? new Promise(resolve => { resolveOld = resolve; }) : Promise.resolve(response([person])));
  vi.stubGlobal("fetch", fetch);
  render(<Home />); const user = userEvent.setup();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Ma");
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "ria");
  await screen.findByRole("option", { name: /Maria/ });
  await act(async () => { resolveOld(response([{ ...person, name: "Nome antigo" }])); });
  expect(screen.queryByText("Nome antigo")).not.toBeInTheDocument();
});

test.each(["Executivo", "Judiciário", "Senado"])("consulta a fonte selecionada: %s", async scope => {
  const provider = scope === "Executivo" ? "executivo" : scope === "Judiciário" ? "judiciario" : "senado";
  const authority = { ...person, provider, role: "Autoridade", institution: "Órgão oficial" };
  const fetch = vi.fn(async (url: string) => response(url.includes("/dashboard") ? { ...dashboard, politician: authority } : [authority]));
  vi.stubGlobal("fetch", fetch);
  render(<Home />); const user = userEvent.setup();
  if (scope === "Senado") await user.selectOptions(screen.getByRole("combobox", { name: "Casa legislativa" }), "senado");
  else await user.click(screen.getByRole("button", { name: scope }));
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Ma");
  await user.click(await screen.findByRole("option", { name: /Maria/ }));
  await screen.findByRole("region", { name: "Perfil" });
  expect(fetch.mock.calls[0][0]).toContain("provider=" + provider);
  expect(fetch.mock.calls.at(-1)?.[0]).toContain("/politicians/" + provider + "/1/dashboard");
  expect(screen.getByText("Dados oficiais consultados no órgão: Órgão oficial.")).toBeVisible();
});

test("foto no resultado vira inicial quando a imagem falha", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response([{ ...person, photo_url: "https://www.camara.leg.br/photo.jpg" }])));
  render(<Home />); const user = userEvent.setup();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria");
  await user.click(screen.getByRole("button", { name: "Buscar" }));
  const image = await screen.findByRole("img", { name: "Foto de Maria" });
  fireEvent.error(image);
  expect(screen.queryByRole("img", { name: "Foto de Maria" })).not.toBeInTheDocument();
  expect(screen.getByText("M", { selector: "span" })).toBeVisible();
});

test("falha nas sugestões mantém a busca manual disponível", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url.includes("/autocomplete") ? { ok: false } : response([person])));
  render(<Home />); const user = userEvent.setup();
  await user.type(screen.getByRole("combobox", { name: "Nome da pessoa" }), "Maria");
  await screen.findByText("Sugestões indisponíveis. Tente o botão Buscar.");
  await user.click(screen.getByRole("button", { name: "Buscar" }));
  expect(await screen.findByRole("button", { name: "Ver dashboard de Maria" })).toBeVisible();
});


import { downloadPdf } from "../lib/api";

test("PDF de outro poder usa nome de perfil e mantém os dados exibidos", async () => {
  const snapshot = { ...dashboard, politician: { ...person, provider: "senado" } };
  const fetch = vi.fn(async () => ({ ok: true, blob: async () => new Blob(["%PDF-"]) }));
  vi.stubGlobal("fetch", fetch);
  vi.stubGlobal("URL", class extends URL { static createObjectURL = () => "blob:report"; static revokeObjectURL = vi.fn(); });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) { expect(this.download).toBe("perfil-1.pdf"); });
  await downloadPdf(snapshot);
  expect(click).toHaveBeenCalledOnce();
  expect(fetch).toHaveBeenCalledWith("http://localhost:8000/reports/pdf", expect.objectContaining({ body: JSON.stringify(snapshot) }));
});
