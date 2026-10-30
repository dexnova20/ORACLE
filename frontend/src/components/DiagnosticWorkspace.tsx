"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DiagnosticReport, FaultHypothesis } from "@/types/api";
import { InteractiveSystemMap } from "./InteractiveSystemMap";
import { EvidenceToHypothesisExplorer } from "./EvidenceToHypothesisExplorer";
import { EvidenceInspector } from "./EvidenceInspector";

interface DiagnosticWorkspaceProps {
  report: DiagnosticReport;
  onRefresh?: () => void;
}

type MobileTab = "map" | "investigation" | "evidence";

export function DiagnosticWorkspace({ report, onRefresh }: DiagnosticWorkspaceProps) {
  const [mobileTab, setMobileTab] = useState<MobileTab>("investigation");
  const [highlightedComponentId, setHighlightedComponentId] = useState<string | null>(null);
  const [activeEvidenceId, setActiveEvidenceId] = useState<string | null>(null);
  const [activeHypothesis, setActiveHypothesis] = useState<FaultHypothesis | null>(
    report.hypotheses.length > 0 ? report.hypotheses[0] : null
  );

  const handleSelectHypothesis = (hypo: FaultHypothesis | null) => {
    setActiveHypothesis(hypo);
    if (hypo) {
      setHighlightedComponentId(hypo.affected_component);
      if (hypo.supporting_evidence_ids.length > 0) {
        setActiveEvidenceId(hypo.supporting_evidence_ids[0]);
      }
    } else {
      setHighlightedComponentId(null);
    }
  };

  const handleSelectComponent = (componentId: string) => {
    setHighlightedComponentId(componentId);
    const matchingHypo = report.hypotheses.find(
      (h) => h.affected_component === componentId || h.affected_component.includes(componentId)
    );
    if (matchingHypo) {
      setActiveHypothesis(matchingHypo);
    }
  };

  const handleSelectEvidence = (evidenceId: string) => {
    setActiveEvidenceId(evidenceId);
    setMobileTab("evidence");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return { text: "Completed", bg: "bg-[#D4FF32]/20 text-[#D4FF32] border-[#D4FF32]/50 font-bold" };
      case "partial":
        return { text: "Partial (Syntax Defect)", bg: "bg-[#D4FF32]/10 text-[#D4FF32] border-[#D4FF32]/30" };
      case "failed":
        return { text: "Failed", bg: "bg-[#F20B91]/20 text-[#F20B91] border-[#F20B91]/50 font-bold" };
      default:
        return { text: status, bg: "bg-black/50 text-[#85858D] border-white/[0.08]" };
    }
  };

  const statusBadge = getStatusBadge(report.status);

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] space-y-3">
      {/* Workspace Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-white/[0.08] bg-[#151519] px-4 py-3 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="flex h-8 w-8 items-center justify-center rounded border border-[#F20B91]/60 bg-black/40 font-black text-[#F20B91] font-mono text-sm">
            Ω
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-black text-[#F5F3EF] tracking-tight uppercase">
                {report.repository_name}
              </h1>
              <span className={`text-[9px] font-mono px-2 py-0.5 rounded border uppercase tracking-wider ${statusBadge.bg}`}>
                {statusBadge.text}
              </span>
              {report.abstention_reason && (
                <span className="rounded bg-[#F20B91]/20 text-[#F20B91] border border-[#F20B91]/40 px-2 py-0.5 text-[9px] font-mono font-bold">
                  Abstained
                </span>
              )}
            </div>
            <p className="text-[11px] text-[#85858D] font-mono truncate max-w-xl">
              Run: {report.run_id} • Source: {report.source_type} • Duration: {(report.duration_ms / 1000).toFixed(2)}s
            </p>
          </div>
        </div>

        {/* Actions & Deliverable Link */}
        <div className="flex items-center space-x-2 font-mono text-xs">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="rounded border border-white/[0.08] bg-black/40 hover:bg-white/[0.08] px-3 py-1.5 text-[#F5F3EF] transition-colors"
            >
              Refresh Data
            </button>
          )}

          <Link
            href={`/reports/${report.run_id}`}
            className="flex items-center space-x-1.5 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-3.5 py-1.5 text-xs transition-all shadow-[0_0_12px_rgba(242,11,145,0.3)]"
          >
            <span>DELIVERABLE REPORT</span>
            <span>→</span>
          </Link>
        </div>
      </div>

      {/* Mobile Tab Switcher */}
      <div className="flex md:hidden rounded border border-white/[0.08] bg-[#151519] p-1 font-mono text-xs shrink-0">
        <button
          onClick={() => setMobileTab("map")}
          className={`flex-1 py-1.5 rounded text-center transition-colors ${
            mobileTab === "map"
              ? "bg-[#D4FF32] text-[#09090B] font-black"
              : "text-[#85858D]"
          }`}
        >
          System Map
        </button>
        <button
          onClick={() => setMobileTab("investigation")}
          className={`flex-1 py-1.5 rounded text-center transition-colors ${
            mobileTab === "investigation"
              ? "bg-[#D4FF32] text-[#09090B] font-black"
              : "text-[#85858D]"
          }`}
        >
          Hypotheses ({report.hypotheses.length})
        </button>
        <button
          onClick={() => setMobileTab("evidence")}
          className={`flex-1 py-1.5 rounded text-center transition-colors ${
            mobileTab === "evidence"
              ? "bg-[#D4FF32] text-[#09090B] font-black"
              : "text-[#85858D]"
          }`}
        >
          Evidence ({report.evidence.length})
        </button>
      </div>

      {/* Living 3-Panel Split View (Desktop) */}
      <div className="hidden md:grid md:grid-cols-12 gap-3 flex-1 min-h-0">
        {/* Panel 1: Interactive System Map (4 cols) */}
        <div className="col-span-4 h-full min-h-0">
          <InteractiveSystemMap
            systemMap={report.system_map}
            highlightedComponentId={highlightedComponentId}
            onSelectComponent={handleSelectComponent}
            isDemo={!report.system_map}
          />
        </div>

        {/* Panel 2: Hypothesis Explorer (4 cols) */}
        <div className="col-span-4 h-full min-h-0">
          <EvidenceToHypothesisExplorer
            hypotheses={report.hypotheses}
            verificationList={report.verification}
            candidateProbes={report.candidate_probes}
            executedProbes={report.executed_probes}
            investigationHistory={report.investigation_history}
            stoppingReason={report.stopping_reason}
            onSelectHypothesis={handleSelectHypothesis}
            onSelectEvidence={handleSelectEvidence}
            onSelectComponent={handleSelectComponent}
          />
        </div>

        {/* Panel 3: Evidence Inspector (4 cols) */}
        <div className="col-span-4 h-full min-h-0">
          <EvidenceInspector
            evidenceList={report.evidence}
            activeEvidenceId={activeEvidenceId}
            supportingEvidenceIds={activeHypothesis?.supporting_evidence_ids || []}
            contradictingEvidenceIds={activeHypothesis?.contradicting_evidence_ids || []}
            onSelectEvidence={handleSelectEvidence}
          />
        </div>
      </div>

      {/* Mobile Single Panel View */}
      <div className="flex-1 md:hidden min-h-0">
        {mobileTab === "map" && (
          <InteractiveSystemMap
            systemMap={report.system_map}
            highlightedComponentId={highlightedComponentId}
            onSelectComponent={handleSelectComponent}
            isDemo={!report.system_map}
          />
        )}
        {mobileTab === "investigation" && (
          <EvidenceToHypothesisExplorer
            hypotheses={report.hypotheses}
            verificationList={report.verification}
            candidateProbes={report.candidate_probes}
            executedProbes={report.executed_probes}
            investigationHistory={report.investigation_history}
            stoppingReason={report.stopping_reason}
            onSelectHypothesis={handleSelectHypothesis}
            onSelectEvidence={handleSelectEvidence}
            onSelectComponent={handleSelectComponent}
          />
        )}
        {mobileTab === "evidence" && (
          <EvidenceInspector
            evidenceList={report.evidence}
            activeEvidenceId={activeEvidenceId}
            supportingEvidenceIds={activeHypothesis?.supporting_evidence_ids || []}
            contradictingEvidenceIds={activeHypothesis?.contradicting_evidence_ids || []}
            onSelectEvidence={handleSelectEvidence}
          />
        )}
      </div>
    </div>
  );
}
