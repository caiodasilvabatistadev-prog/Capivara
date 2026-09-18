import type { DashboardData } from "../lib/api";
export const person = { id: 1, provider: "camara", name: "Maria", party: "ABC", state: "SP", email: null, source_url: "https://www.camara.leg.br/deputados/1" };
export const dashboard: DashboardData = {
  politician: person, year: "2026", fetched_at: "2026-09-18T12:00:00Z", updates: [],
  notice: "Dados oficiais. Não informado é diferente de zero.",
  metrics: [{ label: "Cota parlamentar", value: "R$ 500,00", group: "Gastos públicos", explanation: "Total gasto no ano." }, { label: "Presença em Plenário", value: "10 dias", group: "Presença", explanation: "Dias registrados." }],
  sections: [{ title: "Gastos públicos", blocks: [{ kind: "heading", text: "Cota parlamentar", rows: [] }, { kind: "text", text: "Gastos registrados", rows: [] }, { kind: "table", text: "Gasto mensal da cota parlamentar", rows: [["Mês", "R$"], ["JAN", "100,00"], ["FEV", "400,00"]] }] }],
};
