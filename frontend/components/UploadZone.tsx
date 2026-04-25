"use client";

import { useRef, useState, type DragEvent } from "react";
import type { UploadResponse } from "@/lib/types";

interface Props {
  onFile: (file: File) => void;
  disabled: boolean;
  current: UploadResponse | null;
}

export function UploadZone({ onFile, disabled, current }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      // Surface a soft error by re-routing through onFile with a fake file? No — just no-op.
      // The parent's error path triggers on backend rejection (magic-byte check).
      return;
    }
    onFile(file);
  }

  function handleClick() {
    if (!disabled) inputRef.current?.click();
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={handleClick}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          handleClick();
        }
      }}
      className={[
        "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition",
        dragging
          ? "border-emerald-500 bg-emerald-950/20"
          : "border-slate-700 bg-slate-900/40 hover:border-slate-500",
        disabled ? "cursor-not-allowed opacity-60" : "",
      ].join(" ")}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        disabled={disabled}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = ""; // allow re-picking the same file
        }}
        className="hidden"
      />
      <p className="text-slate-200">
        {dragging ? "Drop the PDF here" : "Drop a PDF here, or click to choose"}
      </p>
      <p className="mt-1 text-xs text-slate-500">PDF only · 50MB max</p>
      {current && (
        <p className="mt-3 text-sm text-slate-400">
          Uploaded <span className="text-slate-200">{current.filename}</span> ({current.size.toLocaleString()} bytes) · id <code className="text-xs text-slate-500">{current.document_id}</code>
        </p>
      )}
    </div>
  );
}
