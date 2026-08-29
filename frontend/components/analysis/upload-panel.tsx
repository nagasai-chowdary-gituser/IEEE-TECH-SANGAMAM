"use client";

import { FileUp, LoaderCircle, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatBytes } from "@/lib/utils";

const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png"];
const ACCEPT_ATTR = "application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png";

interface UploadPanelProps {
  isSubmitting: boolean;
  errorMessage: string | null;
  onAnalyze: (file: File) => void;
}

function isAccepted(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED.some((ext) => name.endsWith(ext));
}

export function UploadPanel({ isSubmitting, errorMessage, onAnalyze }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const assignFile = useCallback((next: File | null) => {
    setLocalError(null);
    if (!next) {
      setFile(null);
      return;
    }
    if (!isAccepted(next)) {
      setFile(null);
      setLocalError("Unsupported file type. Use PDF, JPG, JPEG, or PNG.");
      return;
    }
    setFile(next);
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload</CardTitle>
        <CardDescription>PDF, JPG, JPEG, or PNG. The file is stored and hashed on the server before analysis.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed px-4 py-10 text-center",
            dragOver ? "border-foreground bg-muted/60" : "border-border bg-muted/30",
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
            if (dropped) assignFile(dropped);
          }}
        >
          <FileUp className="mb-3 h-5 w-5 text-muted-foreground" />
          <p className="text-sm font-medium">Drop a document here, or click to browse</p>
          <p className="mt-1 text-xs text-muted-foreground">Accepted: PDF · JPG · JPEG · PNG</p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            className="hidden"
            onChange={(event) => assignFile(event.target.files?.[0] ?? null)}
          />
        </div>

        {file ? (
          <div className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
            <div>
              <p className="text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Clear selected file"
              onClick={() => assignFile(null)}
              disabled={isSubmitting}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : null}

        {(localError || errorMessage) && (
          <p className="text-sm text-destructive">{localError ?? errorMessage}</p>
        )}

        <Button
          type="button"
          disabled={!file || isSubmitting}
          onClick={() => file && onAnalyze(file)}
        >
          {isSubmitting ? (
            <>
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Analyzing…
            </>
          ) : (
            "Analyze document"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
