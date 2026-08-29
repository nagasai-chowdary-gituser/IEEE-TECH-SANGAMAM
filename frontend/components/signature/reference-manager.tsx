"use client";

import { FileUp, LoaderCircle, X } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { createReference, deleteReference, getReferenceImageUrl } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { cn, formatBytes } from "@/lib/utils";
import { useReferences } from "@/hooks/use-references";

const LABELS = ["Principal", "Registrar", "Authorized Signatory", "Judge"];

export function ReferenceManager() {
  const query = useReferences();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("Authorized Signatory");
  const [error, setError] = useState<string | null>(null);
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  const create = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("missing");
      return createReference(file, label);
    },
    onSuccess: () => {
      setFile(null);
      void queryClient.invalidateQueries({ queryKey: ["signature-references"] });
    },
  });
  const remove = useMutation({
    mutationFn: deleteReference,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["signature-references"] }),
  });

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
      <header>
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Certificate & Signature Verification</p>
        <h1 className="mt-2 text-xl font-semibold tracking-tight">Reference signatures</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          The reference signature should be a known authentic signature supplied by an authorized user. The system
          compares visual signature characteristics; it does not independently establish signer identity.
        </p>
      </header>

      <section className="border bg-card p-6">
        <h2 className="text-sm font-semibold">Add reference signature</h2>
        <p className="mt-1 text-sm text-muted-foreground">PNG or JPEG. Crop to the strokes before upload when possible. Blank images are rejected.</p>
        <div
          className={cn(
            "mt-5 flex cursor-pointer flex-col items-center justify-center border border-dashed px-4 py-10 text-center",
            "border-border bg-muted/20",
          )}
          onClick={() => inputRef.current?.click()}
        >
          <FileUp className="mb-3 h-5 w-5 text-muted-foreground" />
          <p className="text-sm font-medium">Drop or browse a signature image</p>
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg"
            className="hidden"
            onChange={(event) => {
              setError(null);
              const next = event.target.files?.[0] ?? null;
              if (next && next.size > 25 * 1024 * 1024) {
                setError("File exceeds 25 MB.");
                setFile(null);
                return;
              }
              setFile(next);
            }}
          />
        </div>
        {file ? (
          <div className="mt-4 flex items-start justify-between gap-3 border bg-background px-3 py-3">
            <div>
              <p className="text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
              {preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt="Reference preview" className="mt-3 max-h-32 border bg-white object-contain" />
              ) : null}
            </div>
            <Button type="button" variant="ghost" size="icon" aria-label="Remove file" onClick={() => setFile(null)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          {LABELS.map((item) => (
            <button
              key={item}
              type="button"
              className={cn("border px-3 py-1.5 text-xs", label === item ? "bg-foreground text-background" : "bg-background hover:bg-muted")}
              onClick={() => setLabel(item)}
            >
              {item}
            </button>
          ))}
        </div>
        {(error || create.error) && (
          <p className="mt-3 text-sm text-destructive">
            {error || (create.error instanceof ApiError ? create.error.message : "Upload failed.")}
          </p>
        )}
        <Button className="mt-5" type="button" disabled={!file || create.isPending} onClick={() => create.mutate()}>
          {create.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
          Save reference signature
        </Button>
      </section>

      <section>
        <h2 className="text-sm font-semibold">Saved references</h2>
        {query.data?.items.length === 0 ? (
          <p className="mt-3 border border-dashed bg-card px-4 py-8 text-center text-sm text-muted-foreground">No reference signatures yet.</p>
        ) : (
          <ul className="mt-3 divide-y border bg-card">
            {(query.data?.items ?? []).map((item) => (
              <li key={item.reference_id} className="flex items-center gap-4 px-4 py-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={getReferenceImageUrl(item.reference_id)} alt="" className="h-12 w-28 border bg-white object-contain" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{item.label ?? "Unlabeled"}</p>
                  <p className="truncate text-xs text-muted-foreground">{item.original_filename}</p>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => remove.mutate(item.reference_id)}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
