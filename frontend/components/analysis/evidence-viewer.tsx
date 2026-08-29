"use client";

import { Minus, Plus, RotateCcw, Maximize2 } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { getArtifactUrl } from "@/lib/api";
import type { ForensicEvidence } from "@/types/analysis";

interface EvidenceViewerProps {
  analysisId: string;
  evidence: ForensicEvidence[];
  emptyLabel: string;
}

export function EvidenceViewer({ analysisId, evidence, emptyLabel }: EvidenceViewerProps) {
  const [index, setIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState(false);
  const current = evidence[Math.min(index, Math.max(evidence.length - 1, 0))];
  const src = useMemo(
    () => (current ? getArtifactUrl(analysisId, current.artifact_id) : null),
    [analysisId, current],
  );

  if (!current || !src) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {evidence.length > 1 ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Button type="button" size="sm" variant="outline" disabled={index === 0} onClick={() => { setIndex((v) => v - 1); setError(false); setZoom(1); }}>
              Prev
            </Button>
            <span>
              {index + 1} / {evidence.length}
            </span>
            <Button type="button" size="sm" variant="outline" disabled={index >= evidence.length - 1} onClick={() => { setIndex((v) => v + 1); setError(false); setZoom(1); }}>
              Next
            </Button>
          </div>
        ) : null}
        <div className="ml-auto flex items-center gap-1">
          <Button type="button" size="icon" variant="outline" aria-label="Zoom out" onClick={() => setZoom((z) => Math.max(0.4, z - 0.25))}>
            <Minus className="h-4 w-4" />
          </Button>
          <Button type="button" size="icon" variant="outline" aria-label="Zoom in" onClick={() => setZoom((z) => Math.min(4, z + 0.25))}>
            <Plus className="h-4 w-4" />
          </Button>
          <Button type="button" size="icon" variant="outline" aria-label="Fit" onClick={() => setZoom(1)}>
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button type="button" size="icon" variant="outline" aria-label="Reset zoom" onClick={() => setZoom(1)}>
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{current.description}</p>
      <div className="overflow-auto rounded-md border bg-muted/40">
        {error ? (
          <p className="px-4 py-10 text-center text-sm text-destructive">Evidence image could not be loaded.</p>
        ) : (
          <div className="flex min-h-[220px] items-center justify-center p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={src}
              alt={current.description}
              className="max-h-[480px] origin-center object-contain transition-transform"
              style={{ transform: `scale(${zoom})` }}
              onError={() => setError(true)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
