import { test, expect } from "@playwright/test";
import { person, dashboard } from "../tests/fixtures";

test("presidente abre perfil interno do partido com logo", async ({ page }) => {
  await page.route("**/rankings?**", route => route.fulfill({ json: { provider: "nacional", metric: "party_fund", year: 2025, status: "ready", title: "Fundo", unit: "BRL", notice: "Fonte TSE", source_url: "", source_as_of: null, covered: 1, total: 1, entries: [{ position: 1, id: null, name: "PL", value: "100", detail: "Repasses", party: { id: 22, president: "Valdemar Costa Neto", logo_url: "/parties/22.png", reviewed_at: "2026-09-18" } }] } }));
  await page.route("**/politicians/partidos/22/dashboard", route => route.fulfill({ json: { ...dashboard, politician: { ...person, provider: "partidos", id: 22, name: "Valdemar Costa Neto", role: "Presidente nacional de partido", institution: "TSE" } } }));
  await page.goto("/rankings", { waitUntil: "domcontentloaded" });
  const card = page.getByRole("heading", { name: "Fundo Partidário — maiores repasses" }).locator("..");
  await card.getByRole("button", { name: "Consultar comparação" }).click();
  await expect(card.locator(".party-logo img")).toHaveCount(1);
  await card.getByRole("link", { name: "Valdemar Costa Neto" }).click();
  await expect(page.getByRole("heading", { name: "Valdemar Costa Neto", exact: true })).toBeVisible();
  await expect(page).toHaveURL("http://localhost:3100/?provider=partidos&id=22");
});

test("emendas e voto entram no PDF e consulta antiga sai ao mudar período", async ({ page }) => {
  const emendas = { title: "Destinos das emendas", blocks: [{ kind: "table", text: "Dados oficiais", rows: [["Órgão", "Finalidade", "Autorizado", "Empenhado", "Pago"], ["Ministério da Saúde", "Atenção básica em SP", "R$ 100,00", "Não informado", "R$ 0,00"]] }] };
  const votos = { title: "Votos e assuntos em Plenário", blocks: [{ kind: "table", text: "Votos oficiais", rows: [["Data", "Objeto", "Contexto", "Voto", "Fonte"], ["2026-09-01", "Destaque sobre imposto", "Tributação", "Não", "https://example.com/voto"]] }] };
  await page.route("**/search/all?**", route => route.fulfill({ json: { items: [person], sources: [] } }));
  await page.route("**/autocomplete/all?**", route => route.fulfill({ json: { items: [person], sources: [] } }));
  await page.route("**/politicians/camara/1/dashboard", route => route.fulfill({ json: dashboard }));
  await page.route("**/politicians/camara/1/amendments?**", route => route.fulfill({ json: emendas }));
  await page.route("**/politicians/camara/1/votes?**", route => route.fulfill({ json: votos }));
  let exported: unknown = null;
  await page.route("**/reports/pdf", async route => {
    if (route.request().method() === "POST") exported = route.request().postDataJSON();
    await route.fulfill({ body: "%PDF-1.4\nReport", headers: { "Content-Type": "application/pdf", "Access-Control-Allow-Origin": "http://localhost:3100", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "POST,OPTIONS" } });
  });
  await page.goto("/", { waitUntil: "domcontentloaded" }); await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Maria"); await page.getByRole("button", { name: "Buscar", exact: true }).click(); await page.getByRole("button", { name: "Puxar a capivara de Maria" }).click();
  await page.getByRole("button", { name: "Consultar emendas e Emendas Pix" }).click();
  await expect(page.getByText("Atenção básica em SP")).toBeVisible();
  await page.getByRole("button", { name: "Consultar votos individuais" }).click();
  await expect(page.getByText("Como votou: Não — contra o objeto votado")).toBeVisible();
  let pending = page.waitForEvent("download"); await page.getByRole("button", { name: "Baixar PDF completo" }).click(); await pending;
  expect(JSON.stringify(exported)).toContain("Destinos das emendas"); expect(JSON.stringify(exported)).toContain("Votos e assuntos em Plenário");
  await page.getByRole("combobox", { name: "Ano das emendas" }).selectOption("2025");
  pending = page.waitForEvent("download"); await page.getByRole("button", { name: "Baixar PDF completo" }).click(); await pending;
  expect(JSON.stringify(exported)).not.toContain("Destinos das emendas"); expect(JSON.stringify(exported)).toContain("Votos e assuntos em Plenário");
});





