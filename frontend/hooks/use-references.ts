import { useQuery } from "@tanstack/react-query";

import { listReferences } from "@/lib/api";

export function useReferences() {
  return useQuery({
    queryKey: ["signature-references"],
    queryFn: listReferences,
  });
}
