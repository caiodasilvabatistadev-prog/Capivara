import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import DashboardMenu from "../components/DashboardMenu";

test("organiza as consultas do perfil e navega para a seção escolhida", async () => {
  const scrollIntoView = vi.fn();
  const target = document.createElement("div");
  target.id = "perfil-bens";
  target.scrollIntoView = scrollIntoView;
  document.body.appendChild(target);
  render(<DashboardMenu />);
  expect(screen.getByRole("navigation", { name: "Consultas disponíveis no perfil" })).toBeVisible();
  expect(screen.getAllByRole("button")).toHaveLength(9);
  await userEvent.click(screen.getByRole("button", { name: /Bens declarados/ }));
  expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
  target.remove();
});

test("muda os indicadores conforme a competência do poder", () => {
  render(<DashboardMenu person={{ id: 1, provider: "executivo", name: "Maria", party: "", state: "Brasil", power: "executivo", email: null, source_url: "x" }} />);
  expect(screen.getByRole("button", { name: /Atos e entregas/ })).toBeVisible();
  expect(screen.queryByRole("button", { name: /Emendas parlamentares/ })).not.toBeInTheDocument();
});
