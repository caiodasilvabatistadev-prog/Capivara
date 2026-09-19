import { test, expect } from "@playwright/test";
import { person, dashboard } from "../tests/fixtures";
test("dashboard, PDF e detalhes permanecem no projeto", async ({ page }) => {
  await page.route("**/search/all?q=*", route => route.fulfill({ json: { items: [person], sources: [] } }));
  await page.route("**/politicians/camara/1/dashboard", route => route.fulfill({ json: dashboard }));
  await page.route("**/reports/pdf", route => route.fulfill({ body: "%PDF-1.4\nReport", headers: { "Content-Type": "application/pdf", "Access-Control-Allow-Origin": "http://localhost:3000", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "POST,OPTIONS" } }));
  await page.addInitScript(() => { window.print = () => { document.body.dataset.printed = "true"; }; });
  await page.goto("/"); await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Maria"); await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.getByRole("button", { name: "Puxar a capivara de Maria" }).click();
  await expect(page.getByText("R$ 500,00")).toBeVisible();
  await expect(page.getByText("10 dias")).toBeVisible();
  await expect(page.getByRole("link")).toHaveCount(0);
  const pending = page.waitForEvent("download"); await page.getByRole("button", { name: "Baixar PDF completo" }).click();
  expect((await pending).suggestedFilename()).toBe("deputado-1.pdf");
  await expect(page).toHaveURL("http://localhost:3000/");
  await page.getByRole("button", { name: "Imprimir a capivara" }).click();
  await expect(page.locator("body")).toHaveAttribute("data-printed", "true");
  await page.getByRole("button", { name: "Voltar aos resultados" }).click();
  await expect(page.getByRole("region", { name: "Perfil" })).toHaveCount(0);
});

for (const [label, provider] of [["Executivo", "executivo"], ["Judiciário", "judiciario"], ["Senado Federal", "senado"]]) {
  test("autocomplete e perfil: " + label, async ({ page }) => {
    const authority = { ...person, provider, role: "Autoridade", institution: "Órgão oficial" };
    await page.route("**/autocomplete/all?**", route => {
      expect(new URL(route.request().url()).pathname).toBe("/autocomplete/all");
      return route.fulfill({ json: { items: [authority], sources: [] } });
    });
    await page.route("**/politicians/" + provider + "/1/dashboard", route => route.fulfill({ json: { ...dashboard, politician: authority } }));
    await page.goto("/");
    await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Ma");
    await page.getByRole("option", { name: /Maria/ }).click();
    await expect(page.getByRole("region", { name: "Perfil" })).toBeVisible();
    await expect(page.getByText("Dados oficiais consultados no órgão: Órgão oficial.")).toBeVisible();
    await expect(page).toHaveURL("http://localhost:3000/");
  });
}

test("estado judicial e fontes seguem para o PDF sem sair do projeto", async ({ page }) => {
  const source = { publisher: "Fonte de teste", url: "https://example.com/fonte", published_at: "2024-05-21" };
  const context = { subject_name: "Maria", reviewed_at: "2026-09-18", notice: "Cobertura parcial de teste.", actions: [], cases: [{ title: "Caso fictício de teste", summary: "Desfecho verificado", category: "criminal", status: "absolvido", court: "Tribunal de teste", case_number: "TESTE-1", status_as_of: "2024-05-21", final_judgment: false, official_source: source, journalism: source }] };
  await page.route("**/search/all?q=*", route => route.fulfill({ json: { items: [person], sources: [] } }));
  await page.route("**/politicians/camara/1/dashboard", route => route.fulfill({ json: dashboard }));
  await page.route("**/politicians/camara/1/context", route => route.fulfill({ json: context }));
  await page.route("**/reports/pdf", async route => {
    if (route.request().method() === "POST") {
      const payload = JSON.stringify(route.request().postDataJSON());
      expect(payload).toContain("Absolvido neste processo");
      expect(payload).toContain("Estado na data: 21/05/2024");
      expect(payload).toContain(source.url);
    }
    await route.fulfill({ body: "%PDF-1.4\nReport", headers: { "Content-Type": "application/pdf", "Access-Control-Allow-Origin": "http://localhost:3000", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "POST,OPTIONS" } });
  });
  await page.goto("/");
  await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Maria");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.getByRole("button", { name: "Puxar a capivara de Maria" }).click();
  await page.getByRole("button", { name: "Notícias e situação judicial", exact: true }).click();
  await page.getByRole("button", { name: "Consultar notícias e registros revisados" }).click();
  await expect(page.getByText("Absolvido neste processo")).toBeVisible();
  await page.getByText("Fontes e datas", { exact: true }).click();
  await expect(page.getByRole("link")).toHaveCount(0);
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar PDF completo" }).click();
  expect((await pending).suggestedFilename()).toBe("deputado-1.pdf");
  await expect(page).toHaveURL("http://localhost:3000/");
});

test("rankings por poder abrem a dashboard dentro do produto", async ({ page }) => {
  await page.route("**/rankings?**", route => {
    const params = new URL(route.request().url()).searchParams;
    expect(params.get("provider")).toBe("camara");
    expect(params.get("metric")).toBe("expenses");
    return route.fulfill({ json: { provider: "camara", metric: "expenses", year: 2026, status: "partial", title: "Gastos", unit: "BRL", notice: "Somente cota parlamentar.", source_url: "https://example.com/fonte", source_as_of: null, covered: 1, total: 2, entries: [{ position: 1, id: 1, name: "Maria", value: "1234.56", detail: "Dado de teste" }] } });
  });
  await page.route("**/politicians/camara/1/dashboard", route => route.fulfill({ json: dashboard }));
  await page.goto("/");
  const card = page.getByRole("article").filter({ has: page.getByRole("heading", { name: "Maiores gastos com cota parlamentar" }) });
  await card.getByRole("button", { name: "Consultar comparação" }).click();
  await expect(card.getByText(/Cobertura parcial: 1 de 2/)).toBeVisible();
  await card.getByText("Fonte e período", { exact: true }).click();
  await expect(card.getByText("https://example.com/fonte", { exact: true })).toBeVisible();
  await card.getByRole("button", { name: "Puxar a capivara de Maria" }).click();
  await expect(page.getByRole("region", { name: "Perfil", exact: true })).toBeVisible();
  await expect(page.getByRole("link")).toHaveCount(0);
  await expect(page).toHaveURL("http://localhost:3000/");
});

test("notícias são buscadas ao abrir perfil e não viram situação judicial", async ({ page }) => {
  await page.route("**/search/all?q=*", route => route.fulfill({ json: { items: [person], sources: [] } }));
  await page.route("**/politicians/camara/1/dashboard", route => route.fulfill({ json: dashboard }));
  await page.route("**/politicians/camara/1/news", route => route.fulfill({ json: { subject_name: "Maria", fetched_at: "2026-09-18T12:00:00Z", notice: "Busca parcial; não confirma culpa.", items: [{ title: "Maria investigada — notícia de exemplo", publisher: "G1", published_at: "2024-05-21T12:00:00Z", source_url: "https://g1.globo.com", reference_url: "https://news.google.com/a", matched_terms: ["investigação"] }] } }));
  await page.goto("/");
  await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Maria");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.getByRole("button", { name: "Puxar a capivara de Maria" }).click();
  const section = page.getByRole("region", { name: "Busca automática de notícias" });
  await expect(section.getByText("Maria investigada — notícia de exemplo")).toBeVisible();
  await expect(section.getByText(/Situação judicial não verificada/)).toBeVisible();
  await section.getByText("Fonte e referência").click();
  await expect(section.getByText("Veículo: https://g1.globo.com")).toBeVisible();
  await expect(page.getByRole("link")).toHaveCount(0);
  await expect(page).toHaveURL("http://localhost:3000/");
});

