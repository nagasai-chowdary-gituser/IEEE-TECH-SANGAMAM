import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type FindingTone = "default" | "success" | "warning" | "danger" | "muted";

export interface KeyFindingItem {
  label: string;
  value: string;
  detail?: string;
  badge?: string;
  tone?: FindingTone;
}

function badgeVariant(tone: FindingTone | undefined) {
  if (tone === "success") return "success" as const;
  if (tone === "warning") return "warning" as const;
  if (tone === "danger") return "danger" as const;
  if (tone === "muted") return "muted" as const;
  return "outline" as const;
}

export function KeyFindings({ items }: { items: KeyFindingItem[] }) {
  const visible = items.filter((item) => item.value.trim().length > 0);
  if (!visible.length) return null;
  return (
    <section className="border bg-card p-5">
      <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Key findings</h2>
      <ul className="mt-4 divide-y">
        {visible.map((item) => (
          <li key={item.label} className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0 sm:flex-row sm:gap-6">
            <p className="w-44 shrink-0 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{item.label}</p>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                {item.badge ? <Badge variant={badgeVariant(item.tone)}>{item.badge}</Badge> : null}
                <p className={cn("text-sm font-medium", item.tone === "danger" && "text-destructive", item.tone === "success" && "text-success", item.tone === "warning" && "text-warning")}>
                  {item.value}
                </p>
              </div>
              {item.detail ? <p className="mt-1 text-sm text-muted-foreground">{item.detail}</p> : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DetailedAnalysis({ title = "Detailed analysis", children }: { title?: string; children: ReactNode }) {
  return (
    <details className="border bg-card p-5">
      <summary className="cursor-pointer text-sm font-semibold">{title}</summary>
      <div className="mt-4 space-y-4">{children}</div>
    </details>
  );
}
