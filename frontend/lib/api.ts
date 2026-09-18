export type Politician = {
  id: number; provider: string; name: string; party: string; state: string;
  role?: string; institution?: string; power?: string;
  email: string | null; photo_url?: string | null; source_url: string;
};
export type Metric = { label: string; value: string; group: string; explanation: string };
export type ReportBlock = { kind: string; text: string; rows: string[][] };
export type DashboardData = {
  politician: Politician; year: string | null; fetched_at: string; updates: string[];
  metrics: Metric[]; sections: { title: string; blocks: ReportBlock[] }[]; notice: string;
};
export const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${api}${path}`, { cache: "no-store", ...(signal ? { signal } : {}) });
  if (!response.ok) throw new Error("Não foi possível consultar os dados oficiais. Tente novamente.");
  return response.json();
}
export async function downloadPdf(data: DashboardData) {
  const response = await fetch(`${api}/reports/pdf`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Não foi possível gerar o PDF. Tente novamente.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = data.politician.provider === "camara" ? `deputado-${data.politician.id}.pdf` : `perfil-${data.politician.id}.pdf`;
  document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
}
