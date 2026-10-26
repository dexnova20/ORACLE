"use client";

import React from "react";
import { DiagnosticReport } from "@/types/api";

interface DiagnosticReportSummaryProps {
  report: DiagnosticReport;
}

export function DiagnosticReportSummary({ report }: DiagnosticReportSummaryProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "partial":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
      case "failed":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
      default:
        return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
    }
  };

  return (
    <div className="space-y-6">
      {/* Run Header Banner */}
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-100 pb-4 dark:border-zinc-800">
          <div>
            <div className="flex items-center space-x-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${getStatusBadge(report.status)}`}>
                Run {report.status}
              </span>
              <span className="font-mono text-xs text-zinc-400">
                {report.run_id}
              </span>
            </div>
            <h3 className="mt-2 text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
              {report.repository_name}
            </h3>
            <p className="mt-0.5 font-mono text-xs text-zinc-500 dark:text-zinc-400">
              {report.repository_url}
            </p>
          </div>

          <div className="text-right text-xs space-y-1">
            <div className="text-zinc-500">
              Source: <span className="font-mono font-medium text-zinc-800 dark:text-zinc-200">{report.source_type}</span>
            </div>
            {report.commit_hash && (
              <div className="text-zinc-500">
                Commit: <span className="font-mono font-medium text-zinc-800 dark:text-zinc-200">{report.commit_hash.slice(0, 8)}</span>
              </div>
            )}
            <div className="text-zinc-500">
              Duration: <span className="font-mono font-medium text-zinc-800 dark:text-zinc-200">{report.duration_ms} ms</span>
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Diagnostic Synthesis</h4>
          <p className="mt-1 text-sm font-medium leading-relaxed text-zinc-800 dark:text-zinc-200">
            {report.summary}
          </p>
        </div>

        {/* Abstention Banner if Present */}
        {report.abstention_reason && (
          <div className="mt-4 rounded-lg border border-purple-200 bg-purple-50 p-4 text-xs text-purple-900 dark:border-purple-900/50 dark:bg-purple-950/30 dark:text-purple-300">
            <div className="font-semibold text-sm mb-1">Deliberate Abstention Notice</div>
            <p>{report.abstention_reason}</p>
          </div>
        )}

        {/* Error message if present */}
        {report.error_message && (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
            <div className="font-semibold text-sm mb-1">Execution Warning / Error</div>
            <p className="font-mono">{report.error_message}</p>
          </div>
        )}
      </div>

      {/* Stage Progression & Coverage */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Completed Stages */}
        <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-800 dark:bg-zinc-950/50">
          <h4 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
            Completed Diagnostic Stages ({report.completed_stages.length})
          </h4>
          <div className="mt-3 flex flex-wrap gap-2">
            {report.completed_stages.map((stg) => (
              <span
                key={stg}
                className="inline-flex items-center space-x-1.5 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 border border-emerald-200 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
              >
                <span>✓</span>
                <span>{stg.replace(/_/g, " ")}</span>
              </span>
            ))}
          </div>
        </div>

        {/* Unsupported / Blocked Stages */}
        <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-800 dark:bg-zinc-950/50">
          <h4 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
            Unsupported / Gated Stages ({report.unsupported_stages.length})
          </h4>
          <div className="mt-3 flex flex-wrap gap-2">
            {report.unsupported_stages.length === 0 ? (
              <span className="text-xs text-zinc-400 italic">None. All requested stages executed.</span>
            ) : (
              report.unsupported_stages.map((stg) => (
                <span
                  key={stg}
                  className="inline-flex items-center space-x-1.5 rounded-md bg-zinc-200/80 px-2.5 py-1 text-xs font-medium text-zinc-700 border border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                >
                  <span>⚠️</span>
                  <span>{stg.replace(/_/g, " ")}</span>
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Prioritized Recommendations */}
      <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
          Prioritized Recommendations ({report.recommendations.length})
        </h4>
        <ul className="mt-3 space-y-2">
          {report.recommendations.map((rec, i) => (
            <li
              key={i}
              className="flex items-start space-x-2 text-xs text-zinc-800 dark:text-zinc-200"
            >
              <span className="font-bold text-amber-500 dark:text-amber-400">→</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
