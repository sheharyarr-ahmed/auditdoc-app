"use client";

interface Props {
  label: string;
}

export function ProgressBar({ label }: Props) {
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-400">{label}</p>
      <div className="h-2 overflow-hidden rounded bg-slate-800">
        <div className="h-full w-1/3 animate-[progress_1.4s_ease-in-out_infinite] bg-gradient-to-r from-emerald-700 via-emerald-400 to-emerald-700" />
      </div>
      <style jsx>{`
        @keyframes progress {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  );
}
