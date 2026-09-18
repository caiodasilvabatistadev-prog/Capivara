import { test, expect } from "@playwright/test";
import { person, dashboard } from "../tests/fixtures";
test("dashboard, PDF e detalhes permanecem no projeto", async ({ page }) => {
  await page.route("**/search?q=*", route => route.fulfill({ json: [person] }));
  await page.route("**/politicians/camara/1/dashboard", route => route.fulfill({ json: dashboard }));
  await page.route("**/reports/pdf", route => route.fulfill({ body: "%PDF-1.4\nReport", headers: { "Content-Type": "application/pdf", "Access-Control-Allow-Origin": "http://localhost:3000", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "POST,OPTIONS" } }));
  await page.addInitScript(() => { window.print = () => { document.body.dataset.printed = "true"; }; });
  await page.goto("/"); await page.getByRole("combobox", { name: "Nome da pessoa" }).fill("Maria"); await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.getByRole("button", { name: "Ver dashboard de Maria" }).click();
  await expect(page.getByText("R$ 500,00")).toBeVisible();
  await expect(page.getByText("10 dias")).toBeVisible();
  await expect(page.getByRole("link")).toHaveCount(0);
  const pending = page.waitForEvent("download"); await page.getByRole("button", { name: "Baixar PDF completo" }).click();
  expect((await pending).suggestedFilename()).toBe("deputado-1.pdf");
  await expect(page).toHaveURL("http://localhost:3000/");
  await page.getByRole("button", { name: "Imprimir dashboard" }).click();
  await expect(page.locator("body")).toHaveAttribute("data-printed", "true");
  await page.getByRole("button", { name: "Voltar aos resultados" }).click();
  await expect(page.getByRole("region", { name: "Perfil" })).toHaveCount(0);
});

for (const [label, provider] of [["Executivo", "executivo"], ["Judiciário", "judiciario"], ["Senado Federal", "senado"]]) {
  test("autocomplete e perfil: " + label, async ({ page }) => {
    const authority = { ...person, provider, role: "Autoridade", institution: "Órgão oficial" };
    await page.route("**/autocomplete?**", route => {
      expect(new URL(route.request().url()).searchParams.get("provider")).toBe(provider);
      return route.fulfill({ json: [authority] });
    });
    await page.route("**/politicians/" + provider + "/1/dashboard", route => route.fulfill({ json: { ...dashboard, politician: authority } }));
    await page.goto("/");
    if (provider === "senado") await page.getByRole("combobox", { name: "Casa legislativa" }).selectOption("senado");
    else await page.getByRole("button", { name: label }).click();
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
  await page.route("**/search?q=*", route => route.fulfill({ json: [person] }));
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
  await page.getByRole("button", { name: "Ver dashboard de Maria" }).click();
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
