import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { analyzeDocument } from "@/lib/api";
import type { AnalysisResponse } from "@/types/analysis";

export function useAnalyzeDocument() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (file: File) => analyzeDocument(file),
    onSuccess: (data: AnalysisResponse) => {
      queryClient.setQueryData(["analysis", data.analysis_id], data);
      void queryClient.invalidateQueries({ queryKey: ["analyses"] });
      router.push(`/analysis/${data.analysis_id}`);
    },
  });
}
