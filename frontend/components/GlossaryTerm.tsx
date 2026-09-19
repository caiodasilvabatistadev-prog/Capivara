import { type ReactNode, useId } from "react";

export const glossary: Record<string, string> = {
  "Emenda Pix": "Nome popular da Transferência Especial: dinheiro indicado por parlamentar e transferido diretamente a estado ou município, com regras públicas de aplicação e prestação de contas.",
  "Transferência especial": "Modalidade oficial da Emenda Pix. O recurso vai diretamente ao estado ou município beneficiário, sem convênio tradicional.",
  "Valor previsto": "Quanto foi planejado para a destinação. Ainda não significa que o dinheiro foi reservado ou transferido.",
  Autorizado: "Valor permitido no orçamento. Não significa que já foi pago.",
  Empenhado: "Valor que o governo reservou formalmente para uma despesa. Ainda pode não ter sido pago.",
  Pago: "Valor cuja ordem de pagamento foi executada. Não comprova, sozinho, que a obra ou serviço foi concluído.",
  Liquidado: "Etapa em que a administração reconhece que o bem ou serviço foi entregue conforme o documento da despesa.",
  CEAP: "Cota para despesas do mandato de deputados, como passagens, combustível e divulgação. Não inclui todos os custos do cargo.",
  CEAPS: "Cota para despesas do mandato de senadores. Não é salário e não inclui todos os custos do cargo.",
  "Fundo Partidário": "Dinheiro público distribuído regularmente aos partidos para manutenção e atividades previstas em lei.",
  "Fundo Eleitoral": "Dinheiro público reservado para financiar campanhas eleitorais no ano da eleição.",
  "Ausência justificada": "Falta acompanhada de uma justificativa registrada pela Casa legislativa. A existência da justificativa não avalia o motivo.",
  "Ausências justificadas no Plenário": "Dias sem presença no Plenário que possuem justificativa registrada pela Câmara.",
  "Ausências não justificadas no Plenário": "Dias sem presença no Plenário para os quais a fonte não mostra justificativa aceita.",
  "Votação nominal": "Votação em que a posição individual de cada parlamentar é registrada e pode ser consultada.",
  "Voto secreto": "Votação em que a posição individual não é divulgada pela fonte oficial.",
};

export default function GlossaryTerm({ term, children }: { term: string; children?: ReactNode }) {
  const explanation = glossary[term];
  const tooltipId = useId();
  if (!explanation) return <>{children || term}</>;
  const label = typeof children === "string" ? children : term;
  return <span className="glossary-term relative inline-block" tabIndex={0} aria-label={label} aria-describedby={tooltipId}>
    <span className="cursor-help border-b border-dotted border-current">{children || term}</span>
    <span id={tooltipId} role="tooltip" className="glossary-tooltip pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-xl bg-slate-950 p-3 text-left text-xs font-normal normal-case leading-relaxed tracking-normal text-white opacity-0 shadow-xl transition-opacity delay-1000 duration-150">{explanation}</span>
  </span>;
}
