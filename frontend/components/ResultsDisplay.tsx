"use client";

import { useState } from "react";
import type { EvaluationResult, Severity } from "@/lib/types";
import { FindingCard } from "@/components/FindingCard";

type SeverityFilter = Severity | "ALL";

interface Props {
  result: EvaluationResult;
}

export function ResultsDisplay({ result }: Props) {
  const [filter, setFilter] = useState<SeverityFilter>("ALL");

  const visible = result.findings.filter((f) => filter === "ALL" || f.severity === filter);

  return (
    <section className="rounded-lg border border-slate-800 bg-surface-raised p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium text-slate-100">Findings</h2>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as SeverityFilter)}
          className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-200"
        >
          <option value="ALL">All severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      <p className="mb-4 text-sm text-slate-400">
        Status: <span className="text-slate-200">{result.status}</span>
        {result.summary && <> · {result.summary}</>}
      </p>

      {visible.length === 0 ? (
        <p className="text-sm text-slate-500">No findings match the current filter.</p>
      ) : (
        <ul className="space-y-3">
          {visible.map((f) => (
            <FindingCard key={f.item_id} finding={f} />
          ))}
        </ul>
      )}
    </section>
  );
}
