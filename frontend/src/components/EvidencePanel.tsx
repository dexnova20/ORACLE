"use client";

import React, { useState } from "react";
import { DiagnosticEvidenceRecord } from "@/types/api";

interface EvidencePanelProps {
  evidenceList: DiagnosticEvidenceRecord[];
  highlightedIds?: string[];
}

export function EvidencePanel({ evidenceList, highlightedIds = [] }: EvidencePanelProps) {
  const [filterType, setFilterType] = useState<string>("all");

  const types = Array.from(new Set(evidenceList.map((e) => e.evidence_type)));

  const filtered = evidenceList.filter((e) => {
    if (filterType === "all") return true;
    return e.evidence_type === filterType;
  });

  const getReliabilityBadge = (rel: string) => {
    switch (rel) {
      case "direct_observation":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "inferred_signal":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
      default:
        return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 pb-2 text-xs dark:border-zinc-800">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setFilterType("all")}
            className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
              filterType === "all"
                ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }`}
          >
            All Evidence ({evidenceList.length})
          </button>
          {types.map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                filterType === t
                  ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-zinc-400">
          Direct observations strictly isolated from ground truth
        </span>
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-xs text-zinc-400 dark:border-zinc-800">
            No evidence records collected for this selection.
          </div>
        ) : (
          filtered.map((record) => {
            const isHighlighted = highlightedIds.includes(record.evidence_id);
            return (
              <div
                key={record.evidence_id}
                id={`evidence-${record.evidence_id}`}
                className={`rounded-lg border p-4 transition-all ${
                  isHighlighted
                    ? "border-amber-400 bg-amber-50/50 shadow-sm dark:border-amber-500/60 dark:bg-amber-950/20"
                    : "border-zinc-200 bg-white hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-zinc-800 dark:text-zinc-200">
                      {record.evidence_id}
                    </span>
                    <span className="rounded bg-zinc-100 px-2 py-0.5 font-mono text-[10px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                      {record.evidence_type}
                    </span>
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${getReliabilityBadge(record.reliability)}`}>
                      {record.reliability}
                    </span>
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    method: <code className="text-zinc-600 dark:text-zinc-300">{record.extraction_method}</code>
                  </div>
                </div>

                <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-300">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-zinc-500">Source:</span>
                    <span className="font-mono">{record.source_component}</span>
                    {record.location && (
                      <>
                        <span className="text-zinc-400">•</span>
                        <span className="font-mono text-amber-700 dark:text-amber-400">
                          {record.location}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Observed payload */}
                <div className="mt-3 rounded bg-zinc-50 p-2.5 font-mono text-xs dark:bg-zinc-950">
                  <div className="text-[10px] uppercase font-semibold text-zinc-400 mb-1">Observed Findings</div>
                  <pre className="overflow-x-auto text-[11px] leading-relaxed text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">
                    {JSON.stringify(record.observed_data, null, 2)}
                  </pre>
                </div>

                {/* Limitations */}
                {record.limitations.length > 0 && (
                  <div className="mt-2 text-[11px] text-zinc-400">
                    <span className="font-medium text-zinc-500">Limitations:</span>{" "}
                    {record.limitations.join("; ")}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
