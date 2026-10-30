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
        <div className="flex items-center space-x-2 px-4 py-2 border-b border-white/[0.08] bg-[#151519] text-xs font-mono shrink-0 mb-3 rounded">
          <span className="text-[#85858D] text-[11px] font-bold">Active Investigation Target:</span>
          <select
            value={selectedRepoId || (repositories.length > 0 ? repositories[0].id : "")}
            onChange={(e) => {
              setSelectedRepoId(e.target.value);
              fetchWorkspace(e.target.value);
            }}
            className="rounded bg-[#09090B] border border-white/[0.1] px-2.5 py-1 text-[#F5F3EF] text-xs font-mono focus:outline-none focus:border-[#F20B91]"
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
        <div className="h-full flex items-center justify-center p-12 text-xs text-[#85858D] font-mono">
          Loading diagnostic investigation workspace...
        </div>
      ) : error ? (
        <div className="max-w-2xl mx-auto my-12 rounded border border-[#F20B91]/50 bg-black/60 p-8 text-center space-y-3 font-mono text-xs">
          <span className="text-[#F20B91] font-bold text-sm block">Error Loading Workspace</span>
          <p className="text-[#F5F3EF] font-sans">{error}</p>
          <button
            onClick={handleRefresh}
            className="rounded border border-white/[0.1] bg-[#151519] hover:bg-white/[0.08] px-4 py-2 text-xs text-[#F5F3EF] transition-colors cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      ) : report ? (
        <DiagnosticWorkspace report={report} onRefresh={handleRefresh} />
      ) : (
        /* Empty State */
        <div className="max-w-2xl mx-auto my-12 rounded border border-dashed border-white/[0.1] bg-[#151519] p-12 text-center space-y-4 font-mono text-xs">
          <div className="h-10 w-10 rounded border border-[#F20B91]/60 bg-black/60 text-[#F20B91] mx-auto flex items-center justify-center font-black text-base">
            Ω
          </div>
          <h2 className="text-base font-black text-[#F5F3EF] uppercase">
            No Active Diagnostic Report
          </h2>
          <p className="text-[#85858D] max-w-md mx-auto leading-relaxed font-sans text-xs">
            The live investigation room presents interactive dependency graphs, evidence inspectors, and causal hypotheses once an investigation has run.
          </p>
          <div className="pt-2">
            <Link
              href="/diagnostics/new"
              className="inline-flex items-center space-x-2 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-5 py-2.5 text-xs tracking-wider transition-colors shadow-sm"
            >
              <span>LAUNCH NEW INVESTIGATION</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      )}
    </AppShell>
  );
}
