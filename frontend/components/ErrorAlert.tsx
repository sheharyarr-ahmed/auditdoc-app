"use client";

interface Props {
  message: string;
  onDismiss?: () => void;
}

export function ErrorAlert({ message, onDismiss }: Props) {
  return (
    <div role="alert" className="flex items-start justify-between gap-3 rounded border border-red-800 bg-red-950/40 p-4 text-sm text-red-200">
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onDismiss}
          className="text-red-300 hover:text-red-100"
        >
          ×
        </button>
      )}
    </div>
  );
}
