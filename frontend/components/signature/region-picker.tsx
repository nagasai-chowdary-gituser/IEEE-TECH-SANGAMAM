"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type { SignatureRegion } from "@/types/signature";

export function RegionPicker({
  imageUrl,
  candidates,
  onSelect,
  pending,
}: {
  imageUrl: string;
  candidates: SignatureRegion[];
  onSelect: (region: { page_number: number; x: number; y: number; width: number; height: number }) => void;
  pending: boolean;
}) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);
  const [box, setBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  function toImageCoords(clientX: number, clientY: number) {
    const img = imgRef.current;
    if (!img) return { x: 0, y: 0 };
    const rect = img.getBoundingClientRect();
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    return {
      x: Math.round((clientX - rect.left) * scaleX),
      y: Math.round((clientY - rect.top) * scaleY),
    };
  }

  return (
    <section className="border bg-card p-5">
      <h2 className="text-sm font-semibold">Select the signature region</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Automatic signature detection was uncertain. Full-document findings above are already complete. Confirm a
        candidate or draw a rectangle so signature integrity (and optional reference comparison) can run on the correct
        region.
      </p>
      <div className="relative mt-4 overflow-auto border bg-muted/20">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Document page"
          className="max-h-[520px] w-full cursor-crosshair object-contain"
          onMouseDown={(event) => {
            event.preventDefault();
            setDrag(toImageCoords(event.clientX, event.clientY));
            setBox(null);
          }}
          onMouseMove={(event) => {
            if (!drag) return;
            const point = toImageCoords(event.clientX, event.clientY);
            setBox({
              x: Math.min(drag.x, point.x),
              y: Math.min(drag.y, point.y),
              w: Math.abs(point.x - drag.x),
              h: Math.abs(point.y - drag.y),
            });
          }}
          onMouseUp={() => setDrag(null)}
        />
      </div>
      {candidates.length ? (
        <div className="mt-4 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Detected candidates</p>
            <Button
              type="button"
              size="sm"
              disabled={pending}
              onClick={() => {
                const item = candidates[0];
                onSelect({ page_number: item.page_number, x: item.x, y: item.y, width: item.width, height: item.height });
              }}
            >
              Use top region and score
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Detection scores only rank crop candidates. They are not originality, final score, or a forgery verdict.
          </p>
          {candidates.map((item, index) => (
            <button
              key={`${item.x}-${item.y}-${index}`}
              type="button"
              disabled={pending}
              className="flex w-full items-center justify-between border px-3 py-2 text-left text-sm hover:bg-muted/40"
              onClick={() => onSelect({ page_number: item.page_number, x: item.x, y: item.y, width: item.width, height: item.height })}
            >
              <span>
                Region {index + 1} · {item.width}×{item.height}
              </span>
              <span className="text-xs text-muted-foreground">detection {item.score ?? "—"}</span>
            </button>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">No automatic candidates. Draw the signature region on the page.</p>
      )}
      {box && box.w > 8 && box.h > 8 ? (
        <Button className="mt-4" type="button" disabled={pending} onClick={() => onSelect({ page_number: 1, x: box.x, y: box.y, width: box.w, height: box.h })}>
          Use drawn region
        </Button>
      ) : null}
    </section>
  );
}
