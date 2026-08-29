"use client";

import { useQuery } from "@tanstack/react-query";

import { ExplanationPanel } from "@/components/analysis/explanation-panel";
import { getExplanation } from "@/lib/api";
import type { AIExplanation } from "@/types/analysis";

export function ExplanationGate({
  analysisId,
  explanation,
  status,
}: {
  analysisId: string;
  explanation: AIExplanation | null;
  status: string;
}) {
  const query = useQuery({
    queryKey: ["explanation", analysisId],
    queryFn: () => getExplanation(analysisId),
    enabled: status === "COMPLETE" && !explanation,
  });
  const value = explanation ?? query.data ?? null;
  if (!value) {
    if (status === "COMPLETE" && query.isLoading) {
      return <p className="text-sm text-muted-foreground">Preparing the evidence summary…</p>;
    }
    return null;
  }
  return <ExplanationPanel explanation={value} />;
}
