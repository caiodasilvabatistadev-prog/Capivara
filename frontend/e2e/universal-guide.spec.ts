import { test, expect } from "@playwright/test";
import { dashboard, person } from "../tests/fixtures";

test("busca única distingue poderes e abre dashboard de governador com PDF", async ({ page }) => {
  const governor = { ...person, provider: "governadores", id: 35, name: "Maria Governo", role: "Governadora", power: "executivo", institution: "Governo SP", party: "ABC" };
  const items = [governor, { ...person, name: "Maria Câmara", power: "legislativo" }];
  await page.route("**/search/all?**", route => route.fulfill({ json: { items, sources: [{provider: "tse2026", name: "Candidaturas TSE 2026", available: false, matches: 0}] } }));
  await page.route("**/autocomplete/all?**", route => route.fulfill({ json: { items, sources: [] } }));
  await page.route("**/politicians/governadores/35/dashboard", route => route.fulfill({ json: { ...dashboard, politician: governor } }));
  await page.route("**/politicians/governadores/35/news", route => route.fulfill({ json: { items: [], notice: "Fixture", fetched_at: "2026-09-18" } }));
  await page.route("**/reports/pdf", route => route.fulfill({ body: "%PDF-1.4\nFixture", headers: { "Content-Type": "application/pdf", "Access-Control-Allow-Origin": "http://localhost:3000" } }));
  await page.goto("/");
  await expect(page.getByRole("combobox", { name: "Casa legislativa" })).toHaveCount(0);
  await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Maria");
  await expect(page.getByRole("option", { name: /Maria Governo/ })).toContainText("Governadora · ABC · Executivo");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page.getByText("Consulta parcial — algumas fontes indisponíveis")).toBeVisible();
  await page.getByRole("button", { name: "Puxar a capivara de Maria Governo" }).click();
  await expect(page.getByRole("region", { name: "Perfil" })).toContainText("Maria Governo");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar PDF completo" }).click();
  expect((await download).suggestedFilename()).toBe("perfil-35.pdf");
});

test("guia explica cargos, mandatos e votos e retorna à busca", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Como funciona", exact: true }).click();
  await expect(page).toHaveURL(/\/como-funciona$/);
  await expect(page.getByRole("heading", { name: "Como a política funciona", exact: true })).toBeVisible();
  await page.locator("details").filter({ has: page.getByText("Ministro do STF", { exact: true }) }).locator("summary").click();
  await expect(page.getByText(/Não é um cargo eleito pelo voto popular/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Como um candidato ajuda a eleger outros?" })).toBeVisible();
  await page.getByRole("button", { name: "Consulta", exact: true }).click();
  await expect(page.getByRole("combobox", { name: "Nome da pessoa" })).toBeVisible();
});

