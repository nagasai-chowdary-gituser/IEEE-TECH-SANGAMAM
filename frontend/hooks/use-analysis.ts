import { useQuery } from "@tanstack/react-query";

import { getAnalysis } from "@/lib/api";

export function useAnalysis(analysisId: string) {
  return useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: () => getAnalysis(analysisId),
    enabled: Boolean(analysisId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PROCESSING" || status === "PENDING" ? 700 : false;
    },
  });
}
