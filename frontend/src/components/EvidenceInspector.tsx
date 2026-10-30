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
        return { text: "Direct Observation", bg: "bg-[#D4FF32]/10 text-[#D4FF32] border-[#D4FF32]/30" };
      case "inferred_signal":
        return { text: "Inferred Signal", bg: "bg-white/[0.05] text-[#F5F3EF] border-white/[0.1]" };
      default:
        return { text: "Limited Context", bg: "bg-black/50 text-[#85858D] border-white/[0.08]" };
    }
  };

  return (
    <div className="flex flex-col h-full rounded border border-white/[0.08] bg-[#151519] overflow-hidden">
      {/* Header */}
      <div className="border-b border-white/[0.08] px-4 py-2.5 bg-[#09090B] shrink-0 font-mono text-xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-[#F20B91] font-black">◈</span>
            <span className="font-bold uppercase tracking-wider text-[#F5F3EF]">
              Evidence Inspector
            </span>
          </div>
          <span className="text-[10px] text-[#85858D]">
            {evidenceList.length} items
          </span>
        </div>

        {/* Filter chips */}
        <div className="flex flex-wrap gap-1 text-[10px]">
          <button
            onClick={() => setFilterType("all")}
            className={`rounded px-2 py-0.5 transition-colors cursor-pointer ${
              filterType === "all"
                ? "bg-[#D4FF32] text-[#09090B] font-black"
                : "text-[#85858D] hover:text-[#F5F3EF]"
            }`}
          >
            All
          </button>
          {availableTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`rounded px-2 py-0.5 transition-colors cursor-pointer ${
                filterType === type
                  ? "bg-[#D4FF32] text-[#09090B] font-black"
                  : "text-[#85858D] hover:text-[#F5F3EF] border border-white/[0.08]"
              }`}
            >
              {type.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Main Inspector View */}
      <div className="flex-1 flex flex-col min-h-0 bg-[#09090B]">
        {/* Evidence List Selector */}
        <div className="max-h-48 overflow-y-auto p-2 space-y-1 border-b border-white/[0.08] bg-[#09090B] shrink-0 font-mono text-xs">
          {filteredList.length === 0 ? (
            <div className="text-center py-4 text-xs text-[#85858D]">
              No evidence matching filter.
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
                  className={`w-full text-left p-2 rounded border transition-all text-xs cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? "border-[#F20B91] bg-[#151519] text-[#F5F3EF] shadow-[0_0_12px_rgba(242,11,145,0.25)] ring-1 ring-[#F20B91]"
                      : "border-white/[0.06] bg-[#151519] text-[#85858D] hover:text-[#F5F3EF] hover:border-white/[0.15]"
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className={`h-1.5 w-1.5 rounded-full ${isSelected ? "bg-[#F20B91]" : "bg-[#85858D]"}`} />
                    <span className="font-bold text-[#F5F3EF] truncate">{rec.evidence_id}</span>
                    <span className="text-[10px] text-[#85858D] truncate">({rec.evidence_type})</span>
                  </div>

                  <div className="flex items-center space-x-1 shrink-0 text-[9px] font-bold">
                    {isSupporting && (
                      <span className="text-[#D4FF32] bg-black px-1.5 py-0.2 rounded border border-[#D4FF32]/40">
                        + Support
                      </span>
                    )}
                    {isContradicting && (
                      <span className="text-[#F20B91] bg-black px-1.5 py-0.2 rounded border border-[#F20B91]/40">
                        - Contradict
                      </span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Selected Evidence Inspector Surface */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs bg-[#09090B]">
          {selectedRecord ? (
            <div className="space-y-4">
              {/* Evidence Title & Metadata */}
              <div className="flex items-start justify-between border-b border-white/[0.08] pb-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-black text-[#F5F3EF]">
                      {selectedRecord.evidence_id}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border ${getReliabilityBadge(selectedRecord.reliability).bg}`}>
                      {getReliabilityBadge(selectedRecord.reliability).text}
                    </span>
                  </div>
                  <span className="text-[11px] text-[#85858D] block mt-0.5">
                    Type: <span className="text-[#D4FF32] font-bold">{selectedRecord.evidence_type}</span> • Method: <span className="text-[#F5F3EF]">{selectedRecord.extraction_method}</span>
                  </span>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-[#85858D] block">Component:</span>
                  <span className="text-xs font-bold text-[#D4FF32]">
                    {selectedRecord.source_component}
                  </span>
                </div>
              </div>

              {/* Source Provenance Coordinates */}
              {selectedRecord.location && (
                <div className="rounded border border-white/[0.08] bg-[#151519] p-3 space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-[#85858D] block">
                    Source Provenance Coordinates
                  </span>
                  <div className="flex items-center space-x-2 text-[11px] text-[#F5F3EF]">
                    <span className="text-[#D4FF32]">📍</span>
                    <span className="text-[#D4FF32] font-bold">
                      {selectedRecord.location}
                    </span>
                  </div>
                </div>
              )}

              {/* Observable Data Payload */}
              {selectedRecord.observed_data && Object.keys(selectedRecord.observed_data).length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-[#85858D] block">
                    Observable Data Payload:
                  </span>
                  <pre className="p-3 rounded border border-white/[0.08] bg-[#151519] text-[#F5F3EF] text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(selectedRecord.observed_data, null, 2)}
                  </pre>
                </div>
              )}

              {/* Limitations Notice */}
              {selectedRecord.limitations && selectedRecord.limitations.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-[#85858D] block">
                    Diagnostic Limitations:
                  </span>
                  <div className="space-y-1">
                    {selectedRecord.limitations.map((lim, idx) => (
                      <div key={idx} className="text-[11px] text-[#85858D] flex items-center space-x-1.5">
                        <span className="text-[#F20B91]">•</span>
                        <span>{lim}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Privacy Scrubbing Notice */}
              <div className="p-2.5 rounded border border-[#D4FF32]/20 bg-[#151519] flex items-center justify-between text-[10px] text-[#85858D]">
                <div className="flex items-center space-x-1.5">
                  <span className="text-[#D4FF32] font-bold">🛡</span>
                  <span>Credentials / JWT tokens redacted prior to storage</span>
                </div>
                <span className="text-[#D4FF32] font-black uppercase">
                  Verified Safe
                </span>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-center text-[#85858D] py-12">
              Select an evidence item from the list above or click an evidence badge in the Hypothesis Explorer.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
