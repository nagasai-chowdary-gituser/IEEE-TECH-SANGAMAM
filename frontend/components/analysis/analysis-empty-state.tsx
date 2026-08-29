import { FileSearch } from "lucide-react";

export function AnalysisEmptyState() {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-dashed bg-card px-6 py-12 text-center">
      <FileSearch className="mb-3 h-6 w-6 text-muted-foreground" />
      <p className="text-sm font-medium">Ready for a document</p>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">
        Choose a PDF, JPG, JPEG, or PNG. After upload, DocuVerify runs the forensic pipeline and opens the saved analysis.
      </p>
    </div>
  );
}
