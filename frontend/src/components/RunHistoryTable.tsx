"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DiagnosticReport } from "@/types/api";

interface RunHistoryTableProps {
  runs: DiagnosticReport[];
  loading?: boolean;
  onRefresh?: () => void;
}

export function RunHistoryTable({ runs, loading, onRefresh }: RunHistoryTableProps) {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredRuns = runs.filter((run) => {
    const matchesSearch =
      run.repository_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      run.run_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (run.summary && run.summary.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus =
      statusFilter === "all" || run.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return { text: "Completed", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
      case "partial":
        return { text: "Partial", bg: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
      case "failed":
        return { text: "Failed", bg: "bg-rose-500/10 text-rose-400 border-rose-500/30" };
      default:
        return { text: status, bg: "bg-slate-800 text-slate-400 border-slate-700" };
    }
  };

  return (
    <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] overflow-hidden space-y-4 p-5">
      {/* Search & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex-1 min-w-[240px] max-w-md relative">
          <input
            type="text"
            placeholder="Search runs by repository name, run ID, or findings..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-[#080d19] px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <div className="flex items-center rounded-lg border border-slate-800 bg-[#080d19] p-1 text-[11px]">
            {["all", "completed", "partial", "failed"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`rounded px-2.5 py-1 font-medium capitalize transition-colors ${
                  statusFilter === st
                    ? "bg-cyan-500 text-slate-950 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-3 py-2 text-xs text-slate-200 transition-colors disabled:opacity-50"
            >
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Table / List */}
      <div className="overflow-x-auto rounded-lg border border-slate-800/80">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-[#080d19] border-b border-slate-800/80 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Repository</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Top Fault Hypothesis</th>
              <th className="px-4 py-3">Evidence</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 bg-[#0a101f]">
            {filteredRuns.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-slate-500 text-xs">
                  {loading ? "Loading diagnostic runs..." : "No diagnostic runs found."}
                </td>
              </tr>
            ) : (
              filteredRuns.map((run) => {
                const badge = getStatusBadge(run.status);
                const topHypo = run.hypotheses.length > 0 ? run.hypotheses[0] : null;

                return (
                  <tr key={run.run_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-medium">
                      <div className="font-bold text-slate-100">{run.repository_name}</div>
                      <div className="font-mono text-[10px] text-slate-500 truncate max-w-[200px]">
                        {run.run_id}
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${badge.bg}`}>
                        {badge.text}
                      </span>
                      {run.abstention_reason && (
                        <span className="block mt-1 text-[10px] text-purple-400">
                          Abstained
                        </span>
                      )}
                    </td>

                    <td className="px-4 py-3">
                      {topHypo ? (
                        <div>
                          <div className="font-semibold text-cyan-300 truncate max-w-[240px]">
                            {topHypo.category_title}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {topHypo.affected_component} ({topHypo.confidence_level})
                          </div>
                        </div>
                      ) : (
                        <span className="text-emerald-400 font-medium">Clean Baseline (No Faults)</span>
                      )}
                    </td>

                    <td className="px-4 py-3 font-mono text-[11px]">
                      <span className="text-slate-200">{run.evidence.length}</span>
                      <span className="text-slate-500"> records</span>
                    </td>

                    <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                      {(run.duration_ms / 1000).toFixed(2)}s
                    </td>

                    <td className="px-4 py-3 text-right space-x-2">
                      <Link
                        href={`/reports/${run.run_id}`}
                        className="rounded border border-slate-700 bg-slate-800/80 hover:bg-slate-700 px-2.5 py-1 text-[11px] font-medium text-slate-200 transition-colors"
                      >
                        Report
                      </Link>
                      <Link
                        href="/workspace"
                        className="rounded border border-cyan-500/40 bg-cyan-950/40 hover:bg-cyan-900/50 px-2.5 py-1 text-[11px] font-medium text-cyan-300 transition-colors"
                      >
                        Workspace
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
