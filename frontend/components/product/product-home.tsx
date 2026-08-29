import Link from "next/link";
import { FileSearch, Landmark, PenLine, Shield } from "lucide-react";

export function ProductHome() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-16 sm:py-20">
      <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">DocuVerify platform</p>
      <h1 className="mt-3 max-w-2xl text-[1.75rem] font-semibold leading-tight tracking-tight">
        Evidence-based document intelligence for forensic review, bid compliance, and certificate analysis.
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
        Choose a workspace. These modules share the same secure upload and local forensic engine. The platform does not
        provide legal proof, government approval, or signer-identity verification.
      </p>

      <div className="mt-12 grid gap-5 lg:grid-cols-3">
        <article className="flex h-full flex-col border bg-card p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-9 w-9 items-center justify-center border bg-background">
              <FileSearch className="h-4 w-4" />
            </div>
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Forensics</span>
          </div>
          <h2 className="mt-5 text-base font-semibold tracking-tight">Document Forensics</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Analyze documents for digital manipulation, visual anomalies, metadata inconsistencies, duplicated regions,
            and logical inconsistencies.
          </p>
          <ul className="mt-4 space-y-1.5 text-sm text-foreground/90">
            <li>Metadata, ELA, and copy-move analysis</li>
            <li>Evidence fusion and risk assessment</li>
          </ul>
          <Link
            href="/forensics"
            className="mt-auto inline-flex h-10 items-center justify-center bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Open forensic workspace
          </Link>
        </article>

        <article className="flex h-full flex-col border bg-card p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-9 w-9 items-center justify-center border bg-background">
              <Landmark className="h-4 w-4" />
            </div>
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Version 2</span>
          </div>
          <h2 className="mt-5 text-base font-semibold tracking-tight">Government Bid Compliance</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Upload an Udyam certificate, extract PAN and GSTIN, verify both through configured services, and run
            integrity analysis in parallel.
          </p>
          <ul className="mt-4 space-y-1.5 text-sm text-foreground/90">
            <li>PAN and GSTIN verification</li>
            <li>Deterministic compliance report</li>
          </ul>
          <Link href="/compliance" className="mt-auto inline-flex h-10 items-center justify-center border bg-background px-4 text-sm font-medium hover:bg-muted">
            Open compliance workspace
          </Link>
        </article>

        <article className="flex h-full flex-col border bg-card p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-9 w-9 items-center justify-center border bg-background">
              <PenLine className="h-4 w-4" />
            </div>
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Version 3</span>
          </div>
          <h2 className="mt-5 text-base font-semibold tracking-tight">Certificate Analyzer</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Full-certificate forensic analysis for suspicious document edits, manipulated content, signature integrity, and
            optional reference-signature comparison.
          </p>
          <ul className="mt-4 space-y-1.5 text-sm text-foreground/90">
            <li>Whole-document manipulation and OCR layout checks</li>
            <li>Independent signature integrity and optional reference match</li>
          </ul>
          <Link href="/signatures" className="mt-auto inline-flex h-10 items-center justify-center border bg-background px-4 text-sm font-medium hover:bg-muted">
            Open certificate analyzer
          </Link>
        </article>
      </div>

      <p className="mt-10 flex items-center gap-2 text-xs text-muted-foreground">
        <Shield className="h-3.5 w-3.5" />
        Not a legal authority. Signer identity is out of scope.
      </p>
    </div>
  );
}
