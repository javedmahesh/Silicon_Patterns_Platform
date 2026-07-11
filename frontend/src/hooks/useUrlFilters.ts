import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * URL-synced filter state — every list view becomes a shareable URL.
 * Pass a STABLE (module-level) array of keys. Changing any non-"page" key resets
 * pagination to page 1 by clearing the "page" param.
 */
export function useUrlFilters<K extends string>(keys: readonly K[]) {
  const [params, setParams] = useSearchParams();

  const values = {} as Record<K, string>;
  for (const k of keys) values[k] = params.get(k) ?? "";

  const setValue = useCallback(
    (key: K, value: string) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value) next.set(key, value);
          else next.delete(key);
          if (key !== ("page" as K)) next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const setMany = useCallback(
    (patch: Partial<Record<K, string>>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch) as [K, string][]) {
            if (v) next.set(k, v);
            else next.delete(k);
          }
          next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const clear = useCallback(() => {
    setParams(new URLSearchParams(), { replace: true });
  }, [setParams]);

  const activeCount = keys.filter((k) => k !== "page" && values[k]).length;

  return { values, setValue, setMany, clear, activeCount };
}
