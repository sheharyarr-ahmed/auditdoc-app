"use client";

import type { Finding, FindingStatus, GovernmentCitation, Severity } from "@/lib/types";

const SEVERITY_STYLE: Record<Severity, string> = {
  CRITICAL: "bg-red-900/40 text-red-200 border-red-700",
  HIGH: "bg-orange-900/40 text-orange-200 border-orange-700",
  MEDIUM: "bg-amber-900/40 text-amber-200 border-amber-700",
  LOW: "bg-slate-800 text-slate-300 border-slate-700",
};

const STATUS_OVERRIDE: Partial<Record<FindingStatus, string>> = {
  PASS: "bg-emerald-900/30 text-emerald-200 border-emerald-700",
  NOT_APPLICABLE: "bg-slate-900/40 text-slate-400 border-slate-700",
};

interface Props {
  finding: Finding;
}

export function FindingCard({ finding }: Props) {
  // PASS / NOT_APPLICABLE override severity styling — a PASS at HIGH severity
  // is good news, not a HIGH-severity flag.
  const style = STATUS_OVERRIDE[finding.status] ?? SEVERITY_STYLE[finding.severity];

  return (
    <li className={`rounded border p-3 ${style}`}>
      <div className="flex items-center justify-between">
        <span className="font-medium">{finding.item_id}</span>
        <span className="text-xs uppercase tracking-wide">
          {finding.status} · {finding.severity}
        </span>
      </div>
      <p className="mt-1 text-sm">{finding.description}</p>
      {finding.supporting_chunks.length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer text-slate-300">
            {finding.supporting_chunks.length} citation
            {finding.supporting_chunks.length === 1 ? "" : "s"}
          </summary>
          <ul className="mt-2 space-y-1">
            {finding.supporting_chunks.map((c, i) => (
              <li key={i} className="rounded bg-slate-900/50 p-2">
                <span className="text-slate-400">
                  p.{c.page} · {c.section}
                </span>
                <p className="mt-1 text-slate-200">{c.text}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
      {finding.gov_citations.length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer text-slate-300">
            {finding.gov_citations.length} government reference
            {finding.gov_citations.length === 1 ? "" : "s"}
          </summary>
          <ul className="mt-2 space-y-1">
            {finding.gov_citations.map((c, i) => (
              <li key={i} className="rounded bg-slate-900/50 p-2">
                <span className="text-slate-400 uppercase tracking-wide text-[10px]">
                  {c.source.replace(/_/g, " ")}
                </span>
                {c.date && (
                  <span className="ml-2 text-slate-500">{c.date}</span>
                )}
                <p className="mt-0.5 text-slate-200">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-slate-600 hover:decoration-slate-400"
                  >
                    {c.title}
                  </a>
                </p>
                {c.summary && (
                  <p className="mt-1 text-slate-400">{c.summary}</p>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}
