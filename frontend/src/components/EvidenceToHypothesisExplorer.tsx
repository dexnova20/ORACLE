"use client";

import React, { useState } from "react";
import { DiagnosticDecisionRecord, DiagnosticProbe, FaultHypothesis, ProbeResult, VerificationOutcome } from "@/types/api";

interface EvidenceToHypothesisExplorerProps {
  hypotheses: FaultHypothesis[];
  verificationList?: VerificationOutcome[];
  candidateProbes?: DiagnosticProbe[];
  executedProbes?: ProbeResult[];
  investigationHistory?: DiagnosticDecisionRecord[];
  stoppingReason?: string | null;
  onSelectHypothesis?: (hypothesis: FaultHypothesis | null) => void;
  onSelectEvidence?: (evidenceId: string) => void;
  onSelectComponent?: (componentId: string) => void;
}

export function EvidenceToHypothesisExplorer({
  hypotheses,
  verificationList = [],
  stoppingReason,
  onSelectHypothesis,
  onSelectEvidence,
  onSelectComponent,
}: EvidenceToHypothesisExplorerProps) {
  const [selectedHypoId, setSelectedHypoId] = useState<string | null>(
    hypotheses.length > 0 ? hypotheses[0].hypothesis_id : null
  );

  const handleHypothesisClick = (hypo: FaultHypothesis) => {
    const nextId = hypo.hypothesis_id === selectedHypoId ? null : hypo.hypothesis_id;
    setSelectedHypoId(nextId);
    if (onSelectHypothesis) {
      onSelectHypothesis(nextId ? hypo : null);
    }
    if (nextId && onSelectComponent) {
      onSelectComponent(hypo.affected_component);
    }
  };

  const getConfidenceBadge = (confidence?: string) => {
    switch (confidence) {
      case "high":
        return { text: "High", bg: "bg-[#F20B91] text-[#09090B] font-black border-[#F20B91]" };
      case "medium":
        return { text: "Medium", bg: "bg-[#D4FF32]/20 text-[#D4FF32] font-bold border-[#D4FF32]/40" };
      case "low":
        return { text: "Low", bg: "bg-black/50 text-[#85858D] border-white/[0.1]" };
      case "uncertain":
      default:
        return { text: "Uncertain", bg: "bg-[#85858D]/20 text-[#85858D] border-[#85858D]/40" };
    }
  };

  const getVerificationBadge = (status?: string) => {
    switch (status) {
      case "verified":
        return { text: "Verified", bg: "bg-[#D4FF32]/20 text-[#D4FF32] font-black border-[#D4FF32]/60" };
      case "partially_verified":
        return { text: "Partially Verified", bg: "bg-[#D4FF32]/10 text-[#D4FF32] border-[#D4FF32]/40 font-bold" };
      case "blocked":
        return { text: "Blocked", bg: "bg-[#F20B91]/20 text-[#F20B91] border-[#F20B91]/50 font-bold" };
      case "unsupported":
        return { text: "Unsupported", bg: "bg-black/50 text-[#85858D] border-white/[0.1]" };
      default:
        return { text: "Candidate", bg: "bg-white/[0.05] text-[#F5F3EF] border-white/[0.1]" };
    }
  };

  return (
    <div className="flex flex-col h-full rounded border border-white/[0.08] bg-[#151519] overflow-hidden">
      {/* Header */}
      <div className="border-b border-white/[0.08] px-4 py-2.5 bg-[#09090B] flex items-center justify-between shrink-0 font-mono text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-[#F20B91] font-black">◈</span>
          <span className="font-bold uppercase tracking-wider text-[#F5F3EF]">
            Hypothesis Ranking ({hypotheses.length})
          </span>
        </div>

        {stoppingReason && (
          <span className="rounded bg-black/60 border border-[#D4FF32]/30 px-2 py-0.5 text-[10px] text-[#D4FF32] font-bold">
            Halt: {stoppingReason.replace(/_/g, " ")}
          </span>
        )}
      </div>

      {/* Main Hypotheses Scroll Area */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3 bg-[#09090B]">
        {hypotheses.length === 0 ? (
          <div className="rounded border border-dashed border-[#D4FF32]/40 bg-black/40 p-8 text-center space-y-2 font-mono text-xs">
            <div className="h-8 w-8 rounded-full bg-[#D4FF32]/20 text-[#D4FF32] mx-auto flex items-center justify-center font-bold">
              ✓
            </div>
            <h3 className="font-black text-sm text-[#D4FF32]">
              Clean Control Baseline
            </h3>
            <p className="text-[11px] text-[#85858D] max-w-sm mx-auto">
              Zero syntax faults, import resolution issues, or telemetry anomalies detected. AST graph verified intact.
            </p>
          </div>
        ) : (
          hypotheses.map((hypo, idx) => {
            const isSelected = hypo.hypothesis_id === selectedHypoId;
            const conf = getConfidenceBadge(hypo.confidence_level);
            const ver = getVerificationBadge(hypo.verification_status);

            return (
              <div
                key={hypo.hypothesis_id}
                onClick={() => handleHypothesisClick(hypo)}
                className={`rounded border transition-all cursor-pointer p-4 space-y-3 ${
                  isSelected
                    ? "border-[#F20B91] bg-[#151519] shadow-[0_0_15px_rgba(242,11,145,0.25)] ring-1 ring-[#F20B91]"
                    : "border-white/[0.08] bg-[#151519] hover:border-white/[0.2]"
                }`}
              >
                {/* Ranking Title & Confidence */}
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-[10px] font-mono">
                      <span className="font-black text-[#F20B91]">
                        #{idx + 1} RANK
                      </span>
                      <span className="text-[#85858D]">•</span>
                      <span className="text-[#85858D]">{hypo.hypothesis_id}</span>
                      <span className="text-[#85858D]">•</span>
                      <span className="text-[#D4FF32] font-bold">{hypo.affected_component}</span>
                    </div>
                    <h3 className="font-black text-xs text-[#F5F3EF] tracking-tight">
                      {hypo.category_title}
                    </h3>
                  </div>

                  <div className="flex flex-col items-end space-y-1 font-mono shrink-0">
                    <span className={`text-[9px] px-2 py-0.5 rounded border uppercase tracking-wider ${conf.bg}`}>
                      {conf.text}
                    </span>
                    <span className={`text-[9px] px-1.5 py-0.2 rounded border ${ver.bg}`}>
                      {ver.text}
                    </span>
                  </div>
                </div>

                {/* Score & Category metrics strip */}
                <div className="flex items-center space-x-4 text-[11px] font-mono border-t border-b border-white/[0.06] py-1.5 text-[#85858D]">
                  <div className="flex items-center space-x-1">
                    <span className="text-[#85858D]">Category:</span>
                    <span className="text-[#F5F3EF] font-bold">{hypo.category}</span>
                  </div>
                  {hypo.relative_ranking_score !== undefined && hypo.relative_ranking_score !== null && (
                    <div className="flex items-center space-x-1">
                      <span className="text-[#85858D]">Score:</span>
                      <span className="text-[#D4FF32] font-bold">
                        {(hypo.relative_ranking_score * 100).toFixed(0)}/100
                      </span>
                    </div>
                  )}
                </div>

                {/* Rationale / Suggestion Text */}
                <p className="text-[11px] text-[#F5F3EF] font-sans leading-relaxed">
                  {hypo.score_rationale || hypo.remediation_suggestion || hypo.category_title}
                </p>

                {/* Supporting / Contradictory Evidence Tokens */}
                <div className="space-y-1.5 pt-1 font-mono text-[10px]">
                  {hypo.supporting_evidence_ids.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[#D4FF32] font-black uppercase text-[9px]">Supporting:</span>
                      {hypo.supporting_evidence_ids.map((evId) => (
                        <button
                          key={evId}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onSelectEvidence) onSelectEvidence(evId);
                          }}
                          className="rounded border border-[#D4FF32]/40 bg-black/60 px-2 py-0.5 text-[#D4FF32] hover:bg-[#D4FF32]/20 transition-colors font-bold cursor-pointer"
                        >
                          + {evId}
                        </button>
                      ))}
                    </div>
                  )}

                  {hypo.contradicting_evidence_ids.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[#F20B91] font-black uppercase text-[9px]">Contradictory:</span>
                      {hypo.contradicting_evidence_ids.map((evId) => (
                        <button
                          key={evId}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onSelectEvidence) onSelectEvidence(evId);
                          }}
                          className="rounded border border-[#F20B91]/40 bg-black/60 px-2 py-0.5 text-[#F20B91] hover:bg-[#F20B91]/20 transition-colors font-bold cursor-pointer"
                        >
                          - {evId}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Verification Log Subsection */}
        {verificationList.length > 0 && (
          <div className="pt-4 border-t border-white/[0.08] space-y-2">
            <span className="font-mono text-[10px] text-[#85858D] uppercase tracking-widest font-black block">
              Active Verification Records ({verificationList.length})
            </span>
            <div className="space-y-1.5 font-mono text-[11px]">
              {verificationList.map((ver, idx) => (
                <div
                  key={`${ver.hypothesis_id}-${idx}`}
                  className="rounded border border-white/[0.08] bg-[#151519] p-2.5 flex items-center justify-between"
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className={ver.status === "verified" ? "text-[#D4FF32] font-black" : "text-[#F20B91] font-black"}>
                      {ver.status === "verified" ? "✓" : "✗"}
                    </span>
                    <span className="text-[#F5F3EF] truncate font-bold">{ver.hypothesis_id} ({ver.method})</span>
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded border uppercase font-bold ${
                    ver.status === "verified"
                      ? "border-[#D4FF32]/40 text-[#D4FF32] bg-black"
                      : "border-[#F20B91]/40 text-[#F20B91] bg-black"
                  }`}>
                    {ver.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
