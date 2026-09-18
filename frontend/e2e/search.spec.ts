import { test, expect } from "@playwright/test";
test("consulta, perfil e impressão", async ({ page }) => {
  const person = { id: 1, provider: "camara", name: "Maria", party: "ABC", state: "SP", email: null, source_url: "https://www.camara.leg.br/deputados/1" };
  await page.route("**/search?q=*", route => route.fulfill({ json: [person] }));
  await page.route("**/politicians/camara/1", route => route.fulfill({ json: person }));
  await page.addInitScript(() => { window.print = () => { document.body.dataset.printed = "true"; }; });
  await page.goto("/"); await page.getByRole("textbox").fill("Maria"); await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.getByRole("button", { name: "Ver perfil de Maria" }).click();
  await expect(page.getByRole("link", { name: "Consultar fonte oficial" })).toHaveAttribute("href", person.source_url);
  await page.getByRole("button", { name: "Imprimir perfil" }).click();
  await expect(page.locator("body")).toHaveAttribute("data-printed", "true");
});
