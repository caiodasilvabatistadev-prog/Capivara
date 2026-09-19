import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import FamiliesPage from "../app/familias/page";

test("apresenta metodologia familiar e mantém Fontes no final do menu", () => {
  render(<FamiliesPage />);
  expect(screen.getByRole("heading", { name: "Famílias na política brasileira" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Critérios de comprovação" })).toBeVisible();
  expect(screen.getByText(/sobrenome igual/)).toBeVisible();
  const menu = within(screen.getByRole("navigation", { name: "Navegação principal" })).getAllByRole("button");
  expect(menu.at(-1)).toHaveTextContent("Fontes");
});
