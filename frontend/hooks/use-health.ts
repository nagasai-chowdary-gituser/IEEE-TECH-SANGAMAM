import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: (query) => (query.state.status === "error" ? 5_000 : 15_000),
  });
}
