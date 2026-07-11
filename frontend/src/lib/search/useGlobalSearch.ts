import { useQuery } from "@tanstack/react-query";

import { useDebounce } from "@/hooks/useDebounce";
import { api } from "@/lib/api/endpoints";

/**
 * Global Search (roadmap) — multi-entity search feeding the command palette.
 *
 * The current API only exposes free-text search for COMPANIES (?q / ?domain).
 * Opportunities and decision makers have no free-text param, so the palette
 * surfaces those as scoped deep-links into their filtered list pages rather than
 * faking server hits. (A dedicated /search endpoint is a future backend follow-up.)
 */
export function useGlobalSearch(term: string) {
  const q = useDebounce(term.trim(), 200);
  const enabled = q.length >= 2;

  const companies = useQuery({
    queryKey: ["search", "companies", q],
    queryFn: () => api.companies({ q, page_size: 6, sort: "lead_score", order: "desc" }),
    enabled,
  });

  return {
    q,
    enabled,
    companies: companies.data?.items ?? [],
    isLoading: enabled && companies.isFetching,
  };
}
