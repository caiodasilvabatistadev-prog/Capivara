import type { Politician } from "../lib/api";

const scope = {
  legislativo: { title: "O que avaliar neste mandato legislativo", does: "Propõe, relata e vota leis; fiscaliza o Executivo; participa do orçamento e pode indicar emendas.", avoids: "Uma emenda não é uma obra executada pelo parlamentar. A execução cabe ao órgão público responsável." },
  executivo: { title: "O que avaliar nesta função executiva", does: "Administra políticas e serviços, executa o orçamento e, conforme o cargo, sanciona leis e assina atos administrativos.", avoids: "Resultado do ministério, governo ou prefeitura só é atribuído à pessoa quando a fonte oficial identifica sua participação e a etapa alcançada." },
  judiciario: { title: "O que avaliar nesta função judicial", does: "Julga processos dentro de sua competência e fundamenta decisões; também pode exercer funções administrativas no tribunal.", avoids: "Não possui emendas parlamentares nem projetos de lei de autoria. Orçamento do tribunal não é gasto pessoal do magistrado." },
};
export default function PowerScope({ person }: { person: Politician }) {
  const item = scope[(person.power || "legislativo") as keyof typeof scope] || scope.legislativo;
  return <section className="mb-10 rounded-2xl border border-emerald-200 bg-emerald-50 p-6" aria-label="Competência do cargo"><p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Competência institucional</p><h3 className="mt-2 text-xl font-bold text-emerald-950">{item.title}</h3><div className="mt-4 grid gap-4 text-sm leading-relaxed md:grid-cols-2"><p><strong>O que faz:</strong> {item.does}</p><p><strong>Cuidado ao interpretar:</strong> {item.avoids}</p></div></section>;
}
