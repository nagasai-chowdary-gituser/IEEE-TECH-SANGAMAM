import { useMutation } from "@tanstack/react-query";

import { askQuestion } from "@/lib/api";

export function useAskQuestion(analysisId: string) {
  return useMutation({
    mutationFn: (question: string) => askQuestion(analysisId, question),
  });
}
