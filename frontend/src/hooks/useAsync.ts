import { useCallback, useEffect, useState } from "react";

export function useAsync<T>(loader: () => Promise<T>, dependencies: readonly unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshToken, setRefreshToken] = useState(0);

  const reload = useCallback(() => setRefreshToken((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    loader()
      .then((result) => {
        if (!controller.signal.aborted) setData(result);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason : new Error("Unexpected request failure"));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // The caller provides stable primitive dependencies for intentional reloads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, refreshToken]);

  return { data, error, loading, reload };
}

