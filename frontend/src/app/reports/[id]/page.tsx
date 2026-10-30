"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { DiagnosticReportView } from "@/components/DiagnosticReportView";
import { getDiagnosticRun } from "@/lib/api";
import { DiagnosticReport } from "@/types/api";

function ReportDetailContent() {
  const params = useParams();
  const runId = params?.id as string;

  const [report, setReport] = useState<DiagnosticReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    let isMounted = true;

    getDiagnosticRun(runId)
      .then((data) => {
        if (isMounted) {
          setReport(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load diagnostic report.";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [runId]);

  return (
    <AppShell activeTargetName={report?.repository_name}>
      {loading ? (
        <div className="max-w-4xl mx-auto rounded border border-white/[0.08] bg-[#151519] p-12 text-center text-xs text-[#85858D] font-mono">
          Loading diagnostic report ({runId || "..."})...
        </div>
      ) : error ? (
        <div className="max-w-2xl mx-auto rounded border border-[#F20B91]/50 bg-black/60 p-8 text-center space-y-3 font-mono text-xs">
          <span className="text-[#F20B91] font-bold text-sm block">Failed to Load Report</span>
          <p className="text-[#F5F3EF] font-sans">{error}</p>
          <div className="pt-2">
            <Link
              href="/history"
              className="inline-block rounded border border-white/[0.1] bg-[#151519] hover:bg-white/[0.08] px-4 py-2 text-xs text-[#F5F3EF] transition-colors"
            >
              ← Back to Run History
            </Link>
          </div>
        </div>
      ) : report ? (
        <DiagnosticReportView report={report} />
      ) : null}
    </AppShell>
  );
}

export default function ReportDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#09090B] text-[#F5F3EF] flex items-center justify-center p-12 text-xs font-mono text-[#85858D]">
          Loading diagnostic deliverable report...
        </div>
      }
    >
      <ReportDetailContent />
    </Suspense>
  );
}
