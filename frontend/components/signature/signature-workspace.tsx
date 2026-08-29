"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { FileUp, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useReferences } from "@/hooks/use-references";
import { ApiError, compareSignature, getReferenceImageUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png"];

function isAccepted(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED.some((ext) => name.endsWith(ext));
}

export function SignatureWorkspace() {
  const router = useRouter();
  const refs = useReferences();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [referenceId, setReferenceId] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: ({ document, refId }: { document: File; refId: string | null }) => compareSignature(document, refId),
    onSuccess: (data) => router.push(`/signatures/${data.comparison_id}`),
  });
  const items = refs.data?.items ?? [];
  const selected = items.find((item) => item.reference_id === referenceId);

  function assignFile(next: File | null) {
    setLocalError(null);
    mutation.reset();
    if (!next) {
      setFile(null);
      return;
    }
    if (!isAccepted(next)) {
      setFile(null);
      setLocalError("Unsupported file type. Use PDF, JPG, JPEG, or PNG.");
      return;
    }
    if (next.size > 25 * 1024 * 1024) {
      setFile(null);
      setLocalError("File exceeds the 25 MB upload limit.");
      return;
    }
    setFile(next);
  }

  function runAnalysis() {
    setLocalError(null);
    if (!file) {
      setLocalError("Upload a certificate first.");
      return;
    }
    mutation.mutate({ document: file, refId: referenceId || null });
  }

  const errorMessage =
    localError ?? (mutation.error instanceof ApiError ? mutation.error.message : mutation.error ? "Certificate analysis could not be started." : null);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
      <header>
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Certificate Analyzer</p>
        <h1 className="mt-2 text-xl font-semibold tracking-tight">Analyze the full certificate</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Analyze the full certificate for suspicious document edits, inserted content, and signature integrity, with
          optional reference-signature comparison. This is technical evidence, not legal authenticity or signer identity.
        </p>
      </header>

      <section className="border bg-card p-6">
        <h2 className="text-sm font-semibold">Upload certificate</h2>
        <p className="mt-1 text-sm text-muted-foreground">PDF, PNG, JPG, or JPEG. Full document analysis. Maximum 25 MB.</p>
        <div
          className={cn(
            "mt-5 flex cursor-pointer flex-col items-center justify-center border border-dashed bg-muted/20 px-4 py-12 text-center",
            dragOver && "border-foreground bg-muted/50",
          )}
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            const dropped = event.dataTransfer.files[0];
            if (dropped) assignFile(dropped);
          }}
        >
          <FileUp className="mb-3 h-5 w-5 text-muted-foreground" />
          <p className="text-sm font-medium">{file ? file.name : "Drag and drop a certificate, or click to browse"}</p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={(event) => assignFile(event.target.files?.[0] ?? null)}
          />
        </div>
      </section>

      <section className="border bg-card p-6">
        <h2 className="text-sm font-semibold">Optional reference signature</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Full certificate analysis runs without a reference. Select one only if you want visual similarity comparison.
        </p>
        {items.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">
            No reference is saved.{" "}
            <Link href="/signatures/references" className="underline-offset-4 hover:underline">
              Add a reference signature
            </Link>{" "}
            if you need this optional stream.
          </p>
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setReferenceId("")}
              className={cn("border px-3 py-3 text-left text-sm", !referenceId ? "border-foreground bg-muted/40" : "hover:bg-muted/30")}
            >
              No reference comparison
            </button>
            {items.map((item) => (
              <button
                key={item.reference_id}
                type="button"
                onClick={() => setReferenceId(item.reference_id)}
                className={cn(
                  "flex items-center gap-3 border px-3 py-3 text-left",
                  referenceId === item.reference_id ? "border-foreground bg-muted/40" : "hover:bg-muted/30",
                )}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={getReferenceImageUrl(item.reference_id)} alt="" className="h-10 w-24 border bg-white object-contain" />
                <span className="text-sm">{item.label ?? item.original_filename}</span>
              </button>
            ))}
          </div>
        )}
        {selected ? <p className="mt-3 text-xs text-muted-foreground">Selected reference: {selected.label ?? selected.original_filename}</p> : null}
      </section>

      {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}
      <Button className="self-start" type="button" disabled={mutation.isPending} onClick={runAnalysis}>
        {mutation.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
        Run certificate analysis
      </Button>
    </div>
  );
}
