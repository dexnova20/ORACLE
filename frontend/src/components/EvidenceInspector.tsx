"use client";

import React, { useState } from "react";
import { DiagnosticEvidenceRecord } from "@/types/api";

interface EvidenceInspectorProps {
  evidenceList: DiagnosticEvidenceRecord[];
  activeEvidenceId?: string | null;
  supportingEvidenceIds?: string[];
  contradictingEvidenceIds?: string[];
  onSelectEvidence?: (evidenceId: string) => void;
}

export function EvidenceInspector({
  evidenceList,
  activeEvidenceId,
  supportingEvidenceIds = [],
  contradictingEvidenceIds = [],
  onSelectEvidence,
}: EvidenceInspectorProps) {
  const [filterType, setFilterType] = useState<string>("all");
  const [selectedId, setSelectedId] = useState<string | null>(
    activeEvidenceId || (evidenceList.length > 0 ? evidenceList[0].evidence_id : null)
  );

  const effectiveSelectedId = activeEvidenceId || selectedId;
  const selectedRecord = evidenceList.find((e) => e.evidence_id === effectiveSelectedId);

  const availableTypes = Array.from(new Set(evidenceList.map((e) => e.evidence_type)));

  const filteredList = evidenceList.filter((e) => {
    if (filterType === "all") return true;
    return e.evidence_type === filterType;
  });

  const getReliabilityBadge = (rel: string) => {
    switch (rel) {
      case "direct_observation":
        return { text: "Direct Observation", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
      case "inferred_signal":
        return { text: "Inferred Signal", bg: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
      default:
        return { text: "Limited Context", bg: "bg-slate-800 text-slate-400 border-slate-700" };
    }
  };

  return (
    <div className="flex flex-col h-full rounded-xl border border-slate-800/80 bg-[#0a0f1d] overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800/80 px-4 py-3 bg-[#0d1322]/80 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-violet-500/10 text-violet-400">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Evidence Inspector
            </span>
          </div>
          <span className="font-mono text-[11px] text-slate-400">
            {evidenceList.length} items
          </span>
        </div>

        {/* Filter chips */}
        <div className="flex flex-wrap gap-1 text-[10px]">
          <button
            onClick={() => setFilterType("all")}
            className={`rounded px-2 py-0.5 font-medium transition-colors ${
              filterType === "all"
                ? "bg-slate-700 text-white"
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            All
          </button>
          {availableTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`rounded px-2 py-0.5 font-medium transition-colors ${
                filterType === type
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-800"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {type.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Main Split Inspector View */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Evidence List Thumbnails */}
        <div className="max-h-48 overflow-y-auto p-3 space-y-1.5 border-b border-slate-800/80 bg-[#080c16]/60 shrink-0">
          {filteredList.length === 0 ? (
            <div className="text-center py-4 text-xs text-slate-500">
              No evidence matching the filter.
            </div>
          ) : (
            filteredList.map((rec) => {
              const isSelected = rec.evidence_id === effectiveSelectedId;
              const isSupporting = supportingEvidenceIds.includes(rec.evidence_id);
              const isContradicting = contradictingEvidenceIds.includes(rec.evidence_id);

              return (
                <button
                  key={rec.evidence_id}
                  onClick={() => {
                    setSelectedId(rec.evidence_id);
                    if (onSelectEvidence) onSelectEvidence(rec.evidence_id);
                  }}
                  className={`w-full text-left p-2 rounded-md border text-xs transition-all flex items-center justify-between cursor-pointer ${
                    isSelected
                      ? "border-cyan-500/80 bg-cyan-950/30 text-cyan-200 font-semibold"
                      : "border-slate-800/60 bg-[#0d1322] text-slate-300 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className="font-mono text-[11px] text-slate-400 shrink-0">
                      {rec.evidence_id}
                    </span>
                    <span className="truncate text-slate-300">
                      {rec.evidence_type.replace("_", " ")}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1.5 shrink-0">
                    {isSupporting && (
                      <span className="rounded bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 text-[9px] font-bold">
                        Supports
                      </span>
                    )}
                    {isContradicting && (
                      <span className="rounded bg-rose-500/20 text-rose-400 px-1.5 py-0.5 text-[9px] font-bold">
                        Contradicts
                      </span>
                    )}
                    <span className="font-mono text-[10px] text-slate-500 truncate max-w-[90px]">
                      {rec.source_component.replace("file:", "")}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Detailed Single Evidence View */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {selectedRecord ? (
            <>
              {/* Evidence Overview Card */}
              <div className="rounded-lg border border-slate-800 bg-[#0d1424] p-3.5 space-y-2.5">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <span className="font-mono font-bold text-cyan-300 text-sm">
                    {selectedRecord.evidence_id}
                  </span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${getReliabilityBadge(selectedRecord.reliability).bg}`}>
                    {getReliabilityBadge(selectedRecord.reliability).text}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">Type:</span>
                    <span className="font-mono font-semibold text-slate-200">
                      {selectedRecord.evidence_type}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Method:</span>
                    <span className="font-mono text-slate-300">
                      {selectedRecord.extraction_method}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-slate-500 block">Source Component:</span>
                    <span className="font-mono text-cyan-400">
                      {selectedRecord.source_component}
                    </span>
                  </div>
                  {selectedRecord.location && (
                    <div className="col-span-2">
                      <span className="text-slate-500 block">File Coordinate:</span>
                      <span className="font-mono text-amber-300 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                        {selectedRecord.location}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Observed Payload / Log Excerpt */}
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1">
                  Observed Data &amp; Sanitized Findings:
                </span>
                <pre className="p-3 rounded-lg border border-slate-800 bg-[#080d19] font-mono text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap max-h-56 leading-relaxed">
                  {JSON.stringify(selectedRecord.observed_data, null, 2)}
                </pre>
              </div>

              {/* Context Limitations */}
              {selectedRecord.limitations && selectedRecord.limitations.length > 0 && (
                <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400 block">
                    Context Boundaries &amp; Limitations:
                  </span>
                  <ul className="list-disc list-inside text-[11px] text-amber-200/90 space-y-0.5">
                    {selectedRecord.limitations.map((lim, i) => (
                      <li key={i}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-center p-6 text-slate-500 text-xs">
              Select an evidence item above or a hypothesis to inspect observable findings.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
