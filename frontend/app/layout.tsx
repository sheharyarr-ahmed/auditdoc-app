import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AuditDoc — Compliance Document Intelligence",
  description: "45-second compliance evaluation with mandatory citations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface text-slate-200 antialiased">
        {children}
      </body>
    </html>
  );
}
