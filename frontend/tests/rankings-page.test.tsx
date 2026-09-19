import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import RankingsPage from "../app/rankings/page";

test("página própria reúne rankings, gráficos e representatividade", () => {
  render(<RankingsPage />);
  expect(screen.getByRole("heading", { name: "Rankings e gráficos públicos" })).toBeVisible();
  expect(screen.getByRole("region", { name: "Dados demográficos autodeclarados" })).toBeVisible();
  expect(screen.getByRole("region", { name: "Atualizações por e-mail" })).toBeVisible();
  expect(screen.getByText("Consultando a base eleitoral do TSE…")).toBeVisible();
});
