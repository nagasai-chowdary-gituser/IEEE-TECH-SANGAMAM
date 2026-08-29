import { useQuery } from "@tanstack/react-query";

import { getCompliance } from "@/lib/api";

export function useCompliance(id: string) {
  return useQuery({
    queryKey: ["compliance", id],
    queryFn: () => getCompliance(id),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PROCESSING" || status === "PENDING" ? 800 : false;
    },
  });
}
