"use client";

import { useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import type { OverlayRegion } from "@/types/signature";

const KIND_COLOR: Record<string, string> = {
  text: "border-warning bg-warning/20",
  copy_move: "border-destructive bg-destructive/20",
  compression: "border-warning bg-warning/15",
  signature: "border-foreground bg-foreground/10",
  suspicious: "border-destructive bg-destructive/15",
};

export function CertificateOverlay({
  imageUrl,
  regions,
}: {
  imageUrl: string;
  regions: OverlayRegion[];
}) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [natural, setNatural] = useState({ w: 1, h: 1 });
  const [selected, setSelected] = useState<number | null>(null);
  const [layers, setLayers] = useState({ text: true, copy_move: true, signature: true, compression: true, suspicious: true });

  const visible = useMemo(
    () => regions.filter((item) => layers[item.kind as keyof typeof layers] !== false),
    [regions, layers],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-[11px] uppercase tracking-wide text-muted-foreground">
        {(["text", "copy_move", "signature"] as const).map((kind) => (
          <button
            key={kind}
            type="button"
            className={cn("border px-2 py-1", layers[kind] ? "bg-muted" : "opacity-50")}
            onClick={() => setLayers((current) => ({ ...current, [kind]: !current[kind] }))}
          >
            {kind.replace("_", " ")}
          </button>
        ))}
      </div>
      <div className="relative overflow-auto border bg-muted/20">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Certificate page"
          className="max-h-[560px] w-full object-contain"
          onLoad={(event) => {
            const img = event.currentTarget;
            setNatural({ w: img.naturalWidth, h: img.naturalHeight });
          }}
        />
        {visible.map((item, index) => {
          const img = imgRef.current;
          if (!img || !natural.w) return null;
          const scaleX = img.clientWidth / natural.w;
          const scaleY = img.clientHeight / natural.h;
          return (
            <button
              key={`${item.kind}-${index}`}
              type="button"
              title={item.explanation}
              className={cn("absolute border-2", KIND_COLOR[item.kind] ?? "border-foreground", selected === index && "ring-2 ring-foreground")}
              style={{
                left: item.x * scaleX,
                top: item.y * scaleY,
                width: Math.max(4, item.width * scaleX),
                height: Math.max(4, item.height * scaleY),
              }}
              onClick={() => setSelected(index)}
            />
          );
        })}
      </div>
      {selected != null && visible[selected] ? (
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{visible[selected].label}.</span> {visible[selected].explanation}
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">Boxes are only drawn for computed regions. Click a box to inspect it.</p>
      )}
    </div>
  );
}
