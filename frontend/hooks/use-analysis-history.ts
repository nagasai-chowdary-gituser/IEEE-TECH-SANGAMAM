import { useQuery } from "@tanstack/react-query";

import { listAnalyses } from "@/lib/api";

export function useAnalysisHistory(limit: number, offset: number) {
  return useQuery({
    queryKey: ["analyses", limit, offset],
    queryFn: () => listAnalyses(limit, offset),
  });
}
