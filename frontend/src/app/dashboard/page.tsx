"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { listDiagnosticRuns, listRepositories, fetchStatus } from "@/lib/api";
import { DiagnosticReport, Repository, SystemStatusResponse } from "@/types/api";

export default function DashboardPage() {
  const [runs, setRuns] = useState<DiagnosticReport[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = useCallback(() => {
    setLoading(true);
    setError(null);

    Promise.allSettled([
      listDiagnosticRuns(),
      listRepositories(),
      fetchStatus(),
    ])
      .then(([runsData, reposData, statusData]) => {
        if (runsData.status === "fulfilled") {
          setRuns(runsData.value);
        }
        if (reposData.status === "fulfilled") {
          setRepositories(reposData.value);
          if (reposData.value.length > 0) {
            setSelectedRepoId((prev) => prev || reposData.value[0].id);
          }
        }
        if (statusData.status === "fulfilled") {
          setStatus(statusData.value);
        }
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load dashboard data.";
        setError(msg);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let isMounted = true;

    Promise.allSettled([
      listDiagnosticRuns(),
      listRepositories(),
      fetchStatus(),
    ])
      .then(([runsData, reposData, statusData]) => {
        if (!isMounted) return;
        if (runsData.status === "fulfilled") {
          setRuns(runsData.value);
        }
        if (reposData.status === "fulfilled") {
          setRepositories(reposData.value);
          if (reposData.value.length > 0) {
            setSelectedRepoId((prev) => prev || reposData.value[0].id);
          }
        }
        if (statusData.status === "fulfilled") {
          setStatus(statusData.value);
        }
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load dashboard data.";
        setError(msg);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const activeRepo = repositories.find((r) => r.id === selectedRepoId);
  const repoRuns = selectedRepoId
    ? runs.filter((r) => r.repository_id === selectedRepoId)
    : runs;

  const getStatusBadge = (runStatus: string) => {
    switch (runStatus) {
      case "completed":
        return { text: "Completed", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
      case "partial":
        return { text: "Partial (Syntax Defect)", bg: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
      case "failed":
        return { text: "Failed", bg: "bg-rose-500/10 text-rose-400 border-rose-500/30" };
      default:
        return { text: runStatus, bg: "bg-slate-800 text-slate-400 border-slate-700" };
    }
  };

  return (
    <AppShell activeTargetName={activeRepo?.name}>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Workspace & Project Selector Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
          <div className="space-y-1">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Diagnostic Workspace Dashboard
            </h1>
            <p className="text-xs text-slate-400">
              Monitor inspected repositories, investigate active defects, and review evidence-backed diagnoses.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {repositories.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium">Target:</span>
                <select
                  value={selectedRepoId}
                  onChange={(e) => setSelectedRepoId(e.target.value)}
                  className="rounded-lg border border-slate-800 bg-[#0d1424] px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
                >
                  <option value="">All Targets ({repositories.length})</option>
                  {repositories.map((repo) => (
                    <option key={repo.id} value={repo.id}>
                      {repo.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <Link
              href="/diagnostics/new"
              className="flex items-center space-x-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-3.5 py-2 text-xs transition-all shadow-sm shadow-cyan-500/20 active:scale-[0.98]"
            >
              <span>+ New Diagnosis</span>
            </Link>
          </div>
        </div>

        {/* System Invariant & Environment Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-4 space-y-1.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              Gateway &amp; API Service
            </span>
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
              <span className="font-mono text-sm font-bold text-slate-100">FastAPI Gateway</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Version: {status?.app.version || "0.1.0"} ({status?.app.environment || "development"})
            </p>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-4 space-y-1.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              State &amp; Persistence Mode
            </span>
            <div className="flex items-center space-x-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  status?.persistence_mode === "durable_postgresql" ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              <span className="font-mono text-sm font-bold text-slate-100">
                {status?.persistence_mode === "durable_postgresql"
                  ? "Durable PostgreSQL"
                  : status?.persistence_mode === "in_memory_transient"
                  ? "In-Memory Transient"
                  : "Standby"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {status?.persistence_mode === "in_memory_transient"
                ? "PostgreSQL offline; targets and reports cached in memory."
                : "PostgreSQL connected via psycopg driver."}
            </p>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-4 space-y-1.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              Container Isolation Preflight
            </span>
            <div className="flex items-center space-x-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  status?.docker_isolation_available ? "bg-emerald-400" : "bg-slate-500"
                }`}
              />
              <span className="font-mono text-sm font-bold text-slate-100">
                {status?.docker_isolation_available ? "Docker Active" : "Host Gated (Safe)"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {status?.docker_isolation_available
                ? "Containerized dynamic verification enabled."
                : "Dynamic execution disabled to prevent untrusted host execution."}
            </p>
          </div>
        </div>

        {/* Error notification if backend unavailable */}
        {error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-4 text-xs text-rose-300 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={loadDashboardData}
              className="rounded bg-rose-900/60 px-2.5 py-1 text-xs font-semibold text-rose-200 hover:bg-rose-800"
            >
              Retry
            </button>
          </div>
        )}

        {/* Recent Diagnostic Runs Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Recent Diagnostic Investigations ({repoRuns.length})
            </h2>
            <Link
              href="/history"
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium transition-colors"
            >
              View Full History →
            </Link>
          </div>

          {loading ? (
            <div className="rounded-xl border border-slate-800 bg-[#0d1424] p-12 text-center text-xs text-slate-500">
              Loading recent diagnostic runs...
            </div>
          ) : repoRuns.length === 0 ? (
            /* Useful Empty State */
            <div className="rounded-xl border border-dashed border-slate-800 bg-[#0d1424]/50 p-12 text-center space-y-3">
              <div className="h-10 w-10 rounded-full bg-slate-800 text-cyan-400 mx-auto flex items-center justify-center font-bold text-base">
                Ω
              </div>
              <h3 className="text-sm font-bold text-slate-200">
                No Diagnostic Runs Found
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No investigations have been executed yet for this target. Register a repository or run a diagnosis to analyze components and generate hypotheses.
              </p>
              <div className="pt-2">
                <Link
                  href="/diagnostics/new"
                  className="inline-flex items-center space-x-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-4 py-2 text-xs transition-colors"
                >
                  <span>Start First Diagnosis</span>
                  <span>→</span>
                </Link>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {repoRuns.slice(0, 6).map((run) => {
                const badge = getStatusBadge(run.status);
                const topHypo = run.hypotheses.length > 0 ? run.hypotheses[0] : null;

                return (
                  <div
                    key={run.run_id}
                    className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-5 space-y-3.5 hover:border-slate-700 transition-all flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-100 text-sm truncate max-w-[180px]">
                          {run.repository_name}
                        </span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${badge.bg}`}>
                          {badge.text}
                        </span>
                      </div>

                      <div className="text-[11px] text-slate-400 font-mono truncate">
                        ID: {run.run_id}
                      </div>

                      {/* Top hypothesis */}
                      <div className="pt-1">
                        <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
                          Primary Finding:
                        </span>
                        {topHypo ? (
                          <div className="rounded bg-[#080d19] p-2.5 border border-slate-800 space-y-0.5">
                            <span className="text-xs font-semibold text-cyan-300 block truncate">
                              {topHypo.category_title}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono block truncate">
                              {topHypo.affected_component} ({topHypo.confidence_level})
                            </span>
                          </div>
                        ) : (
                          <div className="rounded bg-[#080d19] p-2.5 border border-slate-800 text-xs font-medium text-emerald-400">
                            Clean Baseline (No Faults)
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Metadata & Actions */}
                    <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-slate-500 font-mono">
                        {run.evidence.length} evidence • {(run.duration_ms / 1000).toFixed(1)}s
                      </span>

                      <div className="space-x-2">
                        <Link
                          href={`/reports/${run.run_id}`}
                          className="text-slate-400 hover:text-slate-200 transition-colors font-medium"
                        >
                          Report
                        </Link>
                        <Link
                          href="/workspace"
                          className="text-cyan-400 hover:text-cyan-300 font-bold transition-colors"
                        >
                          Workspace →
                        </Link>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
