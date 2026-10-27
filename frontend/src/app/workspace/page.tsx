"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { DiagnosticWorkspace } from "@/components/DiagnosticWorkspace";
import { getLatestDiagnosticReport, listRepositories, listDiagnosticRuns } from "@/lib/api";
import { DiagnosticReport, Repository } from "@/types/api";

export default function WorkspacePage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [report, setReport] = useState<DiagnosticReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspace = useCallback(async (repoId?: string) => {
    try {
      const repos = await listRepositories();
      setRepositories(repos);

      const targetId = repoId || selectedRepoId || (repos.length > 0 ? repos[0].id : "");

      if (targetId) {
        try {
          const latest = await getLatestDiagnosticReport(targetId);
          setReport(latest);
        } catch {
          const allRuns = await listDiagnosticRuns();
          setReport(allRuns.length > 0 ? allRuns[0] : null);
        }
      } else {
        const allRuns = await listDiagnosticRuns();
        setReport(allRuns.length > 0 ? allRuns[0] : null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load diagnostic workspace.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    let isMounted = true;

    (async () => {
      try {
        const repos = await listRepositories();
        if (!isMounted) return;
        setRepositories(repos);

        const targetId = selectedRepoId || (repos.length > 0 ? repos[0].id : "");
        if (targetId) {
          try {
            const latest = await getLatestDiagnosticReport(targetId);
            if (!isMounted) return;
            setReport(latest);
          } catch {
            const allRuns = await listDiagnosticRuns();
            if (!isMounted) return;
            setReport(allRuns.length > 0 ? allRuns[0] : null);
          }
        } else {
          const allRuns = await listDiagnosticRuns();
          if (!isMounted) return;
          setReport(allRuns.length > 0 ? allRuns[0] : null);
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load diagnostic workspace.";
        setError(msg);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [selectedRepoId]);

  const handleRefresh = () => {
    setLoading(true);
    fetchWorkspace();
  };

  const activeRepo = repositories.find((r) => r.id === selectedRepoId);

  return (
    <AppShell activeTargetName={report?.repository_name || activeRepo?.name}>
      {repositories.length > 1 && (
        <div className="flex items-center space-x-2 px-4 py-2 border-b border-slate-800 bg-[#0a0f1d] text-xs shrink-0">
          <span className="text-slate-400 font-mono text-[11px]">Target Workspace:</span>
          <select
            value={selectedRepoId || (repositories.length > 0 ? repositories[0].id : "")}
            onChange={(e) => {
              setSelectedRepoId(e.target.value);
              fetchWorkspace(e.target.value);
            }}
            className="rounded bg-slate-900 border border-slate-700 px-2 py-1 text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
          >
            {repositories.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.id})
              </option>
            ))}
          </select>
        </div>
      )}
      {loading ? (
        <div className="h-full flex items-center justify-center p-12 text-xs text-slate-500 font-mono">
          Loading diagnostic investigation workspace...
        </div>
      ) : error ? (
        <div className="max-w-2xl mx-auto my-12 rounded-xl border border-rose-500/40 bg-rose-950/20 p-8 text-center space-y-3">
          <span className="text-rose-400 font-bold text-sm block">Error Loading Workspace</span>
          <p className="text-xs text-slate-300">{error}</p>
          <button
            onClick={handleRefresh}
            className="rounded-lg bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs text-slate-200 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      ) : report ? (
        <DiagnosticWorkspace report={report} onRefresh={handleRefresh} />
      ) : (
        /* Empty State */
        <div className="max-w-2xl mx-auto my-12 rounded-xl border border-dashed border-slate-800 bg-[#0d1424] p-12 text-center space-y-4">
          <div className="h-12 w-12 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 mx-auto flex items-center justify-center font-bold text-lg font-mono">
            Ω
          </div>
          <h2 className="text-base font-bold text-slate-100">
            No Diagnostic Report Active
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            The live investigation workspace displays system component graphs, evidence inspectors, and causal hypotheses once an investigation has run.
          </p>
          <div className="pt-2">
            <Link
              href="/diagnostics/new"
              className="inline-flex items-center space-x-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-4 py-2.5 text-xs transition-colors shadow-sm"
            >
              <span>Launch New Investigation</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      )}
    </AppShell>
  );
}
