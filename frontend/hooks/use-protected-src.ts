"use client";

import { useEffect, useState } from "react";

import { fetchProtectedBlob } from "@/lib/api";

export function useProtectedSrc(resourceUrl: string | null | undefined) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(Boolean(resourceUrl));

  useEffect(() => {
    if (!resourceUrl) {
      setSrc((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return null;
      });
      setError(false);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(false);

    void fetchProtectedBlob(resourceUrl)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        setSrc((previous) => {
          if (previous && previous !== url) URL.revokeObjectURL(previous);
          return url;
        });
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [resourceUrl]);

  useEffect(() => {
    return () => {
      if (src) URL.revokeObjectURL(src);
    };
  }, [src]);

  return { src, error, loading };
}
