"use client";

import { CHECKLISTS } from "@/lib/types";

interface Props {
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
}

export function ChecklistSelector({ value, onChange, disabled }: Props) {
  return (
    <div className="space-y-2">
      {CHECKLISTS.map((c) => (
        <label
          key={c.id}
          className={[
            "flex items-start gap-3 rounded border p-3 transition",
            value === c.id ? "border-emerald-700 bg-emerald-950/20" : "border-slate-800 hover:border-slate-600",
            disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
          ].join(" ")}
        >
          <input
            type="radio"
            name="checklist"
            value={c.id}
            checked={value === c.id}
            disabled={disabled}
            onChange={() => onChange(c.id)}
            className="mt-1"
          />
          <span>
            <span className="block text-slate-100">{c.label}</span>
            <span className="block text-sm text-slate-400">{c.description}</span>
          </span>
        </label>
      ))}
    </div>
  );
}
