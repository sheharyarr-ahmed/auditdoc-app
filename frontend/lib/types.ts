// Mirror of backend/schemas.py — keep in sync.

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type FindingStatus = "PASS" | "FAIL" | "PARTIAL" | "NOT_APPLICABLE";

export type EvaluationStatusValue =
  | "pending"
  | "running"
  | "completed"
  | "failed";

export interface Chunk {
  page: number;
  section: string;
  text: string;
  metadata: Record<string, string | number | boolean>;
}

export interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  severity: Severity;
}

export interface Finding {
  item_id: string;
  status: FindingStatus;
  severity: Severity;
  description: string;
  supporting_chunks: Chunk[];
  confidence: number;
}

export interface EvaluationResult {
  evaluation_id: string;
  document_id: string;
  checklist_id: string;
  status: EvaluationStatusValue;
  findings: Finding[];
  summary: string;
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  size: number;
  status: string;
}

export interface EvaluateRequest {
  document_id: string;
  checklist_id: string;
}

export interface ApiError {
  error: string;
  status_code: number;
  timestamp: string;
  detail?: string;
}

export const CHECKLISTS: ReadonlyArray<{ id: string; label: string; description: string }> = [
  { id: "soc2_trust_services", label: "SOC 2 Trust Services", description: "Common criteria for security, availability, confidentiality." },
  { id: "esg_basic", label: "ESG Basic", description: "Environmental, social, governance disclosures." },
  { id: "code_review_security", label: "Code Review (Security)", description: "OWASP-leaning security review for source-code PDFs." },
];
