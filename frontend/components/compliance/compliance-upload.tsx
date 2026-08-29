"use client";

import { FileUp, LoaderCircle, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn, formatBytes } from "@/lib/utils";

const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png"];

export function ComplianceUpload({
  isSubmitting,
  errorMessage,
  onAnalyze,
}: {
  isSubmitting: boolean;
  errorMessage: string | null;
  onAnalyze: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const preview = useMemo(
    () => (file && file.type.startsWith("image/") ? URL.createObjectURL(file) : null),
    [file],
  );

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const assign = useCallback((next: File | null) => {
    setLocalError(null);
    if (!next) {
      setFile(null);
      return;
    }
    const name = next.name.toLowerCase();
    if (!ACCEPTED.some((ext) => name.endsWith(ext))) {
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
  }, []);

  return (
    <section className="border bg-card p-6">
      <h2 className="text-sm font-semibold tracking-tight">Upload Udyam Registration Certificate</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        PDF, JPG, JPEG, or PNG. Maximum 25 MB. The file is hashed and stored before extraction and verification.
      </p>
      <div
        className={cn(
          "mt-5 flex cursor-pointer flex-col items-center justify-center border border-dashed px-4 py-12 text-center",
          dragOver ? "border-foreground bg-muted/50" : "border-border bg-muted/20",
          isSubmitting && "pointer-events-none opacity-60",
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
          if (dropped) assign(dropped);
        }}
      >
        <FileUp className="mb-3 h-5 w-5 text-muted-foreground" />
        <p className="text-sm font-medium">Drop the certificate here, or click to browse</p>
        <p className="mt-1 text-xs text-muted-foreground">Accepted: PDF · JPG · JPEG · PNG</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png"
          className="hidden"
          onChange={(event) => assign(event.target.files?.[0] ?? null)}
        />
      </div>
      {file ? (
        <div className="mt-4 flex items-start justify-between gap-3 border bg-background px-3 py-3">
          <div>
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {file.type || "file"} · {formatBytes(file.size)}
            </p>
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Certificate preview" className="mt-3 max-h-40 border object-contain" />
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">PDF preview is available after analysis from stored pages.</p>
            )}
          </div>
          <Button type="button" variant="ghost" size="icon" aria-label="Remove file" onClick={() => assign(null)} disabled={isSubmitting}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : null}
      {(localError || errorMessage) && <p className="mt-3 text-sm text-destructive">{localError ?? errorMessage}</p>}
      <Button type="button" className="mt-5" disabled={!file || isSubmitting} onClick={() => file && onAnalyze(file)}>
        {isSubmitting ? (
          <>
            <LoaderCircle className="h-4 w-4 animate-spin" />
            Starting assessment…
          </>
        ) : (
          "Run compliance assessment"
        )}
      </Button>
    </section>
  );
}
