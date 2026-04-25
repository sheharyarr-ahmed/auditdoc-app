"use client";

import { useState } from "react";
import { ChecklistSelector } from "@/components/ChecklistSelector";
import { ErrorAlert } from "@/components/ErrorAlert";
import { ProgressBar } from "@/components/ProgressBar";
import { ResultsDisplay } from "@/components/ResultsDisplay";
import { UploadZone } from "@/components/UploadZone";
import {
  CHECKLISTS,
  type ApiError,
  type EvaluationResult,
  type UploadResponse,
} from "@/lib/types";

type Phase = "idle" | "uploading" | "uploaded" | "evaluating" | "done" | "error";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [checklistId, setChecklistId] = useState<string>(
    CHECKLISTS[0]?.id ?? "soc2_trust_services",
  );
  const [result, setResult] = useState<EvaluationResult | null>(null);

  const busy = phase === "uploading" || phase === "evaluating";

  async function handleFile(file: File): Promise<void> {
    setError(null);
    setResult(null);
    setPhase("uploading");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/upload", { method: "POST", body: fd });
      if (!res.ok) {
        const err = (await res.json()) as ApiError;
        throw new Error(err.detail ?? err.error);
      }
      setUpload((await res.json()) as UploadResponse);
      setPhase("uploaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setPhase("error");
    }
  }

  async function handleEvaluate(): Promise<void> {
    if (!upload) return;
    setError(null);
    setPhase("evaluating");
    try {
      const res = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ document_id: upload.document_id, checklist_id: checklistId }),
      });
      if (!res.ok) {
        const err = (await res.json()) as ApiError;
        throw new Error(err.detail ?? err.error);
      }
      setResult((await res.json()) as EvaluationResult);
      setPhase("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
      setPhase("error");
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">AuditDoc</h1>
        <p className="mt-2 text-slate-400">
          Compliance document intelligence — 45-second evaluation with mandatory citations.
        </p>
      </header>

      <section className="mb-8 rounded-lg border border-slate-800 bg-surface-raised p-6">
        <h2 className="mb-3 text-lg font-medium text-slate-100">1. Upload PDF</h2>
        <UploadZone onFile={handleFile} disabled={busy} current={upload} />
      </section>

      <section className="mb-8 rounded-lg border border-slate-800 bg-surface-raised p-6">
        <h2 className="mb-3 text-lg font-medium text-slate-100">2. Pick a checklist</h2>
        <ChecklistSelector value={checklistId} onChange={setChecklistId} disabled={busy} />
        <button
          type="button"
          onClick={() => void handleEvaluate()}
          disabled={!upload || busy}
          className="mt-4 rounded bg-emerald-700 px-4 py-2 text-sm font-medium text-emerald-50 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {phase === "evaluating" ? "Evaluating…" : "Run evaluation"}
        </button>
      </section>

      {phase === "evaluating" && (
        <div className="mb-8">
          <ProgressBar label="Calling Claude — this can take up to ~30 seconds…" />
        </div>
      )}

      {error && (
        <div className="mb-8">
          <ErrorAlert message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {result && <ResultsDisplay result={result} />}
    </main>
  );
}
