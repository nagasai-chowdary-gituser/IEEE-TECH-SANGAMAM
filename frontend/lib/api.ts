import type {
  AIExplanation,
  AnalysisListResponse,
  AnalysisResponse,
  AskResponse,
  HealthResponse,
} from "@/types/analysis";
import type { ComplianceListResponse, ComplianceResponse } from "@/types/compliance";
import type {
  ReferenceSignature,
  SignatureComparisonListResponse,
  SignatureComparisonResponse,
} from "@/types/signature";
import { authHeaders, getAccessToken, getDemoToken, persistSession, type AuthSession, type SessionRole } from "@/lib/session";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function withTokenQuery(url: string): string {
  const token = getAccessToken() || getDemoToken();
  if (!token) return url;
  const parsed = new URL(url);
  parsed.searchParams.set("token", token);
  return parsed.toString();
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Fall through to status text.
  }
  if (response.status === 413) return "The file is larger than the server allows.";
  if (response.status === 404) return "The requested analysis or file was not found.";
  if (response.status === 409) return "Analysis is still running. Try again in a moment.";
  return response.statusText || "Request failed.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: authHeaders(init?.headers),
  });
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  return (await response.json()) as T;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function loginWithPassword(username: string, password: string, role: SessionRole): Promise<AuthSession> {
  return request<AuthSession>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
}

export async function getSessionMe(token: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  const session = (await response.json()) as AuthSession;
  persistSession(session);
  return session;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}

export function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(`/api/v1/documents/${analysisId}`);
}

export function listAnalyses(limit = 20, offset = 0): Promise<AnalysisListResponse> {
  return request<AnalysisListResponse>(`/api/v1/documents?limit=${limit}&offset=${offset}`);
}

export function getExplanation(analysisId: string): Promise<AIExplanation> {
  return request<AIExplanation>(`/api/v1/documents/${analysisId}/explanation`);
}

export function askQuestion(analysisId: string, question: string): Promise<AskResponse> {
  return request<AskResponse>(`/api/v1/documents/${analysisId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export function getArtifactUrl(analysisId: string, artifactId: string): string {
  return withTokenQuery(
    `${API_BASE_URL}/api/v1/documents/${analysisId}/artifacts/${encodeURIComponent(artifactId)}`,
  );
}

export function getReportUrl(analysisId: string): string {
  return withTokenQuery(`${API_BASE_URL}/api/v1/documents/${analysisId}/report`);
}

export function analyzeDocument(file: File): Promise<AnalysisResponse> {
  const body = new FormData();
  body.append("file", file);
  return request<AnalysisResponse>("/api/v1/documents/analyze", {
    method: "POST",
    body,
  });
}

export function analyzeCompliance(file: File): Promise<ComplianceResponse> {
  const body = new FormData();
  body.append("file", file);
  return request<ComplianceResponse>("/api/v1/compliance/analyze", {
    method: "POST",
    body,
  });
}

export function getCompliance(id: string): Promise<ComplianceResponse> {
  return request<ComplianceResponse>(`/api/v1/compliance/${id}`);
}

export function listCompliance(limit = 20, offset = 0): Promise<ComplianceListResponse> {
  return request<ComplianceListResponse>(`/api/v1/compliance?limit=${limit}&offset=${offset}`);
}

export function getComplianceReportUrl(id: string): string {
  return withTokenQuery(`${API_BASE_URL}/api/v1/compliance/${id}/report`);
}

export function listReferences(): Promise<{ items: ReferenceSignature[]; total: number }> {
  return request("/api/v1/signatures/references");
}

export function createReference(file: File, label?: string): Promise<ReferenceSignature> {
  const body = new FormData();
  body.append("file", file);
  if (label) body.append("label", label);
  return request("/api/v1/signatures/references", { method: "POST", body });
}

export function deleteReference(id: string): Promise<{ status: string }> {
  return request(`/api/v1/signatures/references/${id}`, { method: "DELETE" });
}

export function getReferenceImageUrl(id: string, variant: "original" | "normalized" = "original"): string {
  return withTokenQuery(`${API_BASE_URL}/api/v1/signatures/references/${id}/image?variant=${variant}`);
}

export function compareSignature(file: File, referenceId?: string | null): Promise<SignatureComparisonResponse> {
  const body = new FormData();
  body.append("file", file);
  if (referenceId) body.append("reference_id", referenceId);
  return request("/api/v1/signatures/compare", { method: "POST", body });
}

export function getSignatureComparison(id: string): Promise<SignatureComparisonResponse> {
  return request(`/api/v1/signatures/comparisons/${id}`);
}

export function listSignatureComparisons(limit = 20, offset = 0): Promise<SignatureComparisonListResponse> {
  return request(`/api/v1/signatures/comparisons?limit=${limit}&offset=${offset}`);
}

export function setSignatureRegion(
  id: string,
  region: { page_number: number; x: number; y: number; width: number; height: number },
): Promise<SignatureComparisonResponse> {
  return request(`/api/v1/signatures/comparisons/${id}/region`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(region),
  });
}

export function getSignatureArtifactUrl(id: string, artifactId: string): string {
  return withTokenQuery(
    `${API_BASE_URL}/api/v1/signatures/comparisons/${id}/artifacts/${encodeURIComponent(artifactId)}`,
  );
}

export function getSignatureReportUrl(id: string): string {
  return withTokenQuery(`${API_BASE_URL}/api/v1/signatures/comparisons/${id}/report`);
}
