import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AIExplanation } from "@/types/analysis";

const LAYER_LABEL: Record<string, string> = {
  metadata: "Metadata",
  ela: "ELA",
  copy_move: "Copy-Move",
  document_intelligence: "Document Intelligence",
  fusion: "Fusion",
};

export function ExplanationPanel({ explanation }: { explanation: AIExplanation }) {
  const title =
    explanation.source === "ai"
      ? "AI explanation of analysis results"
      : "Evidence summary (deterministic fallback)";
  const caption =
    explanation.source === "ai"
      ? "This text explains the completed forensic results. It does not calculate scores or invent evidence."
      : "The AI provider is unavailable or not configured. This summary is generated from the deterministic fusion result.";

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{caption}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-relaxed">
        <section>
          <h3 className="text-[11px] uppercase tracking-wide text-muted-foreground">Summary</h3>
          <p className="mt-1">{explanation.summary}</p>
        </section>
        <section>
          <h3 className="text-[11px] uppercase tracking-wide text-muted-foreground">Why this assessment?</h3>
          <p className="mt-1">{explanation.risk_explanation}</p>
        </section>
        {explanation.strongest_evidence.length ? (
          <section>
            <h3 className="text-[11px] uppercase tracking-wide text-muted-foreground">Strongest evidence</h3>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {explanation.strongest_evidence.map((item, index) => (
                <li key={`${item.layer}-${index}`}>
                  <span className="font-medium">{LAYER_LABEL[item.layer] ?? item.layer}:</span> {item.explanation}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <section>
          <h3 className="text-[11px] uppercase tracking-wide text-muted-foreground">Evidence agreement</h3>
          <p className="mt-1">{explanation.corroboration_explanation}</p>
        </section>
        <section>
          <h3 className="text-[11px] uppercase tracking-wide text-muted-foreground">Limitations</h3>
          <p className="mt-1">{explanation.limitations_explanation}</p>
        </section>
        <section>
          <h3 className="text-[11px] uppercase tracking-wide text-muted-foreground">Recommended next step</h3>
          <p className="mt-1">{explanation.recommended_next_step}</p>
        </section>
        <p className="text-xs text-muted-foreground">{explanation.disclaimer}</p>
      </CardContent>
    </Card>
  );
}
