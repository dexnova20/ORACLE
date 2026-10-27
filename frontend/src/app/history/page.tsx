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
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div className="space-y-1">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Diagnostic Run History
            </h1>
            <p className="text-xs text-slate-400">
              Audit log of previous investigations, findings, stopping rationales, and evidence records.
            </p>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-4 text-xs text-rose-300 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={loadRuns}
              className="rounded bg-rose-900/60 px-2.5 py-1 text-xs font-semibold text-rose-200 hover:bg-rose-800"
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
