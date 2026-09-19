import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import DirtyRecordsPage from "../app/fichas-sujas/page";

test("lista somente inelegíveis e condenados com prisão confirmada", () => {
  render(<DirtyRecordsPage />);
  expect(screen.getByRole("heading", { name: "Fichas sujas" })).toBeVisible();
  expect(screen.getByText(/clique em um cartão para puxar a capivara/i)).toBeVisible();
  expect(screen.getByRole("heading", { name: "Jair Bolsonaro" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Roberto Jefferson" })).toBeVisible();
  expect(screen.getAllByText("Inelegível")).toHaveLength(5);
  expect(screen.getAllByText(/Condenad[oa]/)).toHaveLength(5);
  expect(screen.getAllByText("Preso")).toHaveLength(2);
  expect(screen.getAllByText("Domiciliar")).toHaveLength(2);
  expect(screen.getByRole("heading", { name: "Arthur do Val (Mamãe Falei)" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Carla Zambelli" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Puxar a capivara de Roberto Jefferson" })).toHaveAttribute("href", "/fichas-sujas/roberto-jefferson");
});
