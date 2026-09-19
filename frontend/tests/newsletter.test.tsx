import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import Newsletter from "../components/Newsletter";
import { person } from "./fixtures";

test("cadastra novidades somente com consentimento", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: "Inscrição registrada.", confirmation_required: true }) });
  vi.stubGlobal("fetch", fetch);
  render(<Newsletter />); const user = userEvent.setup();
  const button = screen.getByRole("button", { name: "Quero receber" });
  expect(button).toBeDisabled();
  await user.type(screen.getByRole("textbox", { name: "Seu e-mail" }), "pessoa@example.org");
  await user.click(screen.getByRole("checkbox")); await user.click(button);
  expect(await screen.findByRole("status")).toHaveTextContent("Inscrição registrada");
  expect(fetch).toHaveBeenCalledWith("http://localhost:8000/subscriptions", expect.objectContaining({ method: "POST" }));
});

test("cria alerta ligado ao político e mostra erro", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  render(<Newsletter person={person} />); const user = userEvent.setup();
  expect(screen.getByRole("heading", { name: "Receba alertas sobre Maria" })).toBeVisible();
  await user.type(screen.getByRole("textbox", { name: "Seu e-mail" }), "pessoa@example.org");
  await user.click(screen.getByRole("checkbox")); await user.click(screen.getByRole("button", { name: "Criar alerta" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível concluir");
});
