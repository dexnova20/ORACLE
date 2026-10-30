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
        return { text: "Completed", bg: "bg-[#D4FF32]/20 text-[#D4FF32] border-[#D4FF32]/50 font-bold" };
      case "partial":
        return { text: "Partial", bg: "bg-[#D4FF32]/10 text-[#D4FF32] border-[#D4FF32]/30" };
      case "failed":
        return { text: "Failed", bg: "bg-[#F20B91]/20 text-[#F20B91] border-[#F20B91]/50 font-bold" };
      default:
        return { text: status, bg: "bg-black/50 text-[#85858D] border-white/[0.08]" };
    }
  };

  return (
    <div className="rounded border border-white/[0.08] bg-[#151519] overflow-hidden space-y-4 p-5 font-mono text-xs">
      {/* Search & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex-1 min-w-[240px] max-w-md relative">
          <input
            type="text"
            placeholder="Search runs by repository, ID, or causal summary..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded border border-white/[0.08] bg-[#09090B] px-3.5 py-2 text-xs text-[#F5F3EF] placeholder-[#85858D] focus:border-[#F20B91] focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <div className="flex items-center rounded border border-white/[0.08] bg-black/40 p-0.5 text-[11px]">
            {["all", "completed", "partial", "failed"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`rounded px-2.5 py-1 capitalize transition-colors cursor-pointer ${
                  statusFilter === st
                    ? "bg-[#D4FF32] text-[#09090B] font-black"
                    : "text-[#85858D] hover:text-[#F5F3EF]"
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
              className="rounded border border-white/[0.08] bg-[#09090B] hover:bg-white/[0.08] px-3 py-1.5 text-xs text-[#F5F3EF] transition-colors disabled:opacity-40 cursor-pointer"
            >
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Table / List */}
      <div className="overflow-x-auto rounded border border-white/[0.08]">
        <table className="w-full text-left text-xs text-[#F5F3EF]">
          <thead className="bg-[#09090B] border-b border-white/[0.08] text-[10px] text-[#85858D] uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Repository &amp; Run ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Primary Fault Hypothesis</th>
              <th className="px-4 py-3">Evidence Records</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04] bg-[#151519]">
            {filteredRuns.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[#85858D]">
                  {loading ? "Loading diagnostic runs..." : "No diagnostic records match the query."}
                </td>
              </tr>
            ) : (
              filteredRuns.map((run) => {
                const badge = getStatusBadge(run.status);
                const topHypothesis = run.hypotheses.length > 0 ? run.hypotheses[0] : null;

                return (
                  <tr key={run.run_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-black text-[#F5F3EF]">{run.repository_name}</div>
                      <div className="text-[10px] text-[#85858D] font-mono">{run.run_id}</div>
                    </td>

                    <td className="px-4 py-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider ${badge.bg}`}>
                        {badge.text}
                      </span>
                    </td>

                    <td className="px-4 py-3">
                      {topHypothesis ? (
                        <div className="max-w-xs truncate">
                          <span className="text-[#F20B91] font-bold">[{topHypothesis.hypothesis_id}]</span>{" "}
                          <span className="text-[#F5F3EF]">{topHypothesis.category_title}</span>
                        </div>
                      ) : (
                        <span className="text-[#D4FF32]">Clean Baseline (No Faults)</span>
                      )}
                    </td>

                    <td className="px-4 py-3 text-[#85858D]">
                      {run.evidence.length} records
                    </td>

                    <td className="px-4 py-3 text-[#85858D]">
                      {(run.duration_ms / 1000).toFixed(2)}s
                    </td>

                    <td className="px-4 py-3 text-right space-x-2">
                      <Link
                        href={`/reports/${run.run_id}`}
                        className="rounded border border-white/[0.1] bg-[#09090B] hover:border-[#D4FF32] px-2.5 py-1 text-[11px] text-[#F5F3EF] transition-colors"
                      >
                        Report
                      </Link>
                      <Link
                        href="/workspace"
                        className="rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-2.5 py-1 text-[11px] transition-colors"
                      >
                        Workspace →
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
