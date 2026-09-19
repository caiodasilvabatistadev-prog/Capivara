import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import SourcesPage from "../app/fontes/page";

test("lista fontes por categoria e mantém Fontes como último item do menu", () => {
  render(<SourcesPage />);
  expect(screen.getByRole("heading", { name: "Todas as fontes do projeto" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Processos e situação judicial" })).toBeVisible();
  expect(screen.getAllByRole("link", { name: "Consultar fonte" }).length).toBeGreaterThan(10);
  const buttons = within(screen.getByRole("navigation", { name: "Navegação principal" })).getAllByRole("button");
  expect(buttons.at(-1)).toHaveTextContent("Fontes");
});
