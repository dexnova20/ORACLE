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
        return { text: "Completed", bg: "bg-[#D4FF32]/20 text-[#D4FF32] border-[#D4FF32]/50 font-bold" };
      case "partial":
        return { text: "Partial (Syntax Defect)", bg: "bg-[#D4FF32]/10 text-[#D4FF32] border-[#D4FF32]/30" };
      case "failed":
        return { text: "Failed", bg: "bg-[#F20B91]/20 text-[#F20B91] border-[#F20B91]/50 font-bold" };
      default:
        return { text: runStatus, bg: "bg-black/50 text-[#85858D] border-white/[0.08]" };
    }
  };

  return (
    <AppShell activeTargetName={activeRepo?.name}>
      <div className="space-y-6 max-w-7xl mx-auto font-sans">
        {/* Workspace Header & Action Console */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-black tracking-tight text-[#F5F3EF] uppercase">
                Engineering Operations Console
              </h1>
              <span className="font-mono text-[10px] text-[#D4FF32] bg-black/50 px-2 py-0.5 rounded border border-[#D4FF32]/30 font-bold">
                DIAGNOSTIC TELEMETRY
              </span>
            </div>
            <p className="text-xs text-[#85858D]">
              Active repository targets, persistence status, and evidence-ranked failure investigations.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {repositories.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-[#85858D] font-mono font-bold">Target:</span>
                <select
                  value={selectedRepoId}
                  onChange={(e) => setSelectedRepoId(e.target.value)}
                  className="rounded border border-white/[0.08] bg-[#151519] px-3 py-1.5 text-xs text-[#F5F3EF] focus:border-[#F20B91] focus:outline-none font-mono"
                >
                  <option value="">All Repositories ({repositories.length})</option>
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
              className="flex items-center space-x-1.5 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-4 py-2 text-xs tracking-wider transition-all shadow-[0_0_15px_rgba(242,11,145,0.3)] active:scale-[0.98]"
            >
              <span>+ NEW DIAGNOSIS</span>
            </Link>
          </div>
        </div>

        {/* System Invariant & Telemetry State Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
          {/* Gateway Health */}
          <div className="rounded border border-white/[0.08] bg-[#151519] p-4 space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase text-[#85858D] font-bold">
              <span>API Gateway Service</span>
              <span className="text-[#D4FF32] font-black">ONLINE</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-[#D4FF32] shadow-[0_0_8px_rgba(212,255,50,0.8)]" />
              <span className="text-sm font-black text-[#F5F3EF]">FastAPI Daemon</span>
            </div>
            <p className="text-[11px] text-[#85858D] font-sans">
              Version: {status?.app.version || "0.1.0"} ({status?.app.environment || "production-ready"})
            </p>
          </div>

          {/* Persistence Mode */}
          <div className="rounded border border-white/[0.08] bg-[#151519] p-4 space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase text-[#85858D] font-bold">
              <span>Persistence Engine</span>
              <span className={status?.persistence_mode === "durable_postgresql" ? "text-[#D4FF32] font-black" : "text-[#85858D] font-bold"}>
                {status?.persistence_mode === "durable_postgresql" ? "DURABLE" : "TRANSIENT"}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  status?.persistence_mode === "durable_postgresql" ? "bg-[#D4FF32]" : "bg-[#85858D]"
                }`}
              />
              <span className="text-sm font-black text-[#F5F3EF]">
                {status?.persistence_mode === "durable_postgresql"
                  ? "PostgreSQL Active"
                  : status?.persistence_mode === "in_memory_transient"
                  ? "In-Memory Transient"
                  : "Standby"}
              </span>
            </div>
            <p className="text-[11px] text-[#85858D] font-sans">
              {status?.persistence_mode === "in_memory_transient"
                ? "PostgreSQL offline; targets and reports securely cached in memory."
                : "PostgreSQL connected via psycopg driver with durable transactional state."}
            </p>
          </div>

          {/* Docker Isolation Preflight */}
          <div className="rounded border border-white/[0.08] bg-[#151519] p-4 space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase text-[#85858D] font-bold">
              <span>Container Isolation</span>
              <span className={status?.docker_isolation_available ? "text-[#D4FF32] font-black" : "text-[#85858D] font-bold"}>
                {status?.docker_isolation_available ? "AVAILABLE" : "GATED (SAFE)"}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  status?.docker_isolation_available ? "bg-[#D4FF32]" : "bg-[#85858D]"
                }`}
              />
              <span className="text-sm font-black text-[#F5F3EF]">
                {status?.docker_isolation_available ? "Docker Sandbox" : "Host Gated (Safe)"}
              </span>
            </div>
            <p className="text-[11px] text-[#85858D] font-sans">
              {status?.docker_isolation_available
                ? "Dynamic verification enabled in restricted containers with dropped capabilities."
                : "Dynamic execution safely disabled to prevent untrusted host compromise."}
            </p>
          </div>
        </div>

        {/* Error notification if backend unavailable */}
        {error && (
          <div className="rounded border border-[#F20B91]/50 bg-black/60 p-4 text-xs text-[#F20B91] flex items-center justify-between font-mono font-bold">
            <span>{error}</span>
            <button
              onClick={loadDashboardData}
              className="rounded bg-[#F20B91] px-3 py-1 text-xs text-[#09090B] font-black hover:bg-[#d60a80] cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Recent Diagnostic Investigations Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32]" />
              <h2 className="text-xs font-mono font-black uppercase tracking-wider text-[#F5F3EF]">
                Recent Diagnostic Investigations ({repoRuns.length})
              </h2>
            </div>
            <Link
              href="/history"
              className="text-xs font-mono text-[#D4FF32] hover:underline font-bold transition-colors"
            >
              View Full History →
            </Link>
          </div>

          {loading ? (
            <div className="rounded border border-white/[0.08] bg-[#151519] p-12 text-center text-xs text-[#85858D] font-mono">
              Loading recent diagnostic runs...
            </div>
          ) : repoRuns.length === 0 ? (
            /* Purposeful Empty State */
            <div className="rounded border border-dashed border-white/[0.1] bg-[#151519] p-12 text-center space-y-4">
              <div className="h-10 w-10 rounded-full bg-black/60 border border-[#F20B91]/60 text-[#F20B91] mx-auto flex items-center justify-center font-black text-sm font-mono">
                Ω
              </div>
              <h3 className="text-base font-black text-[#F5F3EF] uppercase">
                No Diagnostic Investigations Executed
              </h3>
              <p className="text-xs text-[#85858D] max-w-md mx-auto">
                No diagnostic runs have been performed yet for this target. Register a local or remote repository to analyze AST structures and generate ranked hypotheses.
              </p>
              <div className="pt-2">
                <Link
                  href="/diagnostics/new"
                  className="inline-flex items-center space-x-1.5 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-5 py-2.5 text-xs tracking-wider transition-colors"
                >
                  <span>START FIRST DIAGNOSIS</span>
                  <span>→</span>
                </Link>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {repoRuns.slice(0, 6).map((run) => {
                const badge = getStatusBadge(run.status);
                const topHypo = run.hypotheses.length > 0 ? run.hypotheses[0] : null;

                return (
                  <div
                    key={run.run_id}
                    className="rounded border border-white/[0.08] bg-[#151519] p-4 space-y-3 hover:border-white/[0.2] transition-all flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-black text-[#F5F3EF] text-xs truncate max-w-[180px]">
                          {run.repository_name}
                        </span>
                        <span className={`text-[9px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${badge.bg}`}>
                          {badge.text}
                        </span>
                      </div>

                      <div className="text-[10px] text-[#85858D] font-mono truncate">
                        ID: {run.run_id}
                      </div>

                      {/* Primary Causal Finding */}
                      <div className="pt-1">
                        <span className="text-[9px] text-[#85858D] uppercase font-mono font-bold tracking-wider block mb-1">
                          Primary Finding:
                        </span>
                        {topHypo ? (
                          <div className="rounded bg-[#09090B] p-2.5 border border-white/[0.06] space-y-0.5">
                            <span className="text-xs font-bold text-[#F5F3EF] block truncate">
                              {topHypo.category_title}
                            </span>
                            <span className="text-[10px] text-[#D4FF32] font-mono block truncate font-bold">
                              {topHypo.affected_component} ({topHypo.confidence_level})
                            </span>
                          </div>
                        ) : (
                          <div className="rounded bg-[#09090B] p-2.5 border border-white/[0.06] text-xs font-bold text-[#D4FF32]">
                            Clean Baseline (No Faults)
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Metadata & Actions */}
                    <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px] font-mono">
                      <span className="text-[#85858D]">
                        {run.evidence.length} evidence • {(run.duration_ms / 1000).toFixed(1)}s
                      </span>

                      <div className="space-x-3">
                        <Link
                          href={`/reports/${run.run_id}`}
                          className="text-[#85858D] hover:text-[#F5F3EF] transition-colors"
                        >
                          Report
                        </Link>
                        <Link
                          href="/workspace"
                          className="text-[#D4FF32] hover:underline font-black transition-colors"
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
