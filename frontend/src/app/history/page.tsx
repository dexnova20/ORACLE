"use client";

import React, { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { RunHistoryTable } from "@/components/RunHistoryTable";
import { listDiagnosticRuns } from "@/lib/api";
import { DiagnosticReport } from "@/types/api";

export default function HistoryPage() {
  const [runs, setRuns] = useState<DiagnosticReport[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(() => {
    setLoading(true);
    setError(null);
    listDiagnosticRuns()
      .then((data) => {
        setRuns(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load diagnostic run history.";
        setError(msg);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let isMounted = true;
    listDiagnosticRuns()
      .then((data) => {
        if (isMounted) {
          setRuns(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load diagnostic run history.";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <AppShell>
      <div className="space-y-5 max-w-7xl mx-auto">
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-[#D4FF32]" />
              <h1 className="text-xl font-black tracking-tight text-[#F5F3EF] font-mono uppercase">
                Diagnostic Run History
              </h1>
            </div>
            <p className="text-xs text-[#85858D] font-sans">
              Chronological audit log of previous investigations, findings, stopping rationales, and evidence records.
            </p>
          </div>
        </div>

        {error && (
          <div className="rounded border border-[#F20B91]/50 bg-black/60 p-4 text-xs text-[#F20B91] flex items-center justify-between font-mono font-bold">
            <span>{error}</span>
            <button
              onClick={loadRuns}
              className="rounded bg-[#F20B91] px-3 py-1 text-xs font-black text-[#09090B] hover:bg-[#d60a80] cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        <RunHistoryTable runs={runs} loading={loading} onRefresh={loadRuns} />
      </div>
    </AppShell>
  );
}
