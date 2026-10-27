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
    // Find matching hypothesis for component if available
    const matchingHypo = report.hypotheses.find((h) => h.affected_component === componentId || h.affected_component.includes(componentId));
    if (matchingHypo) {
      setActiveHypothesis(matchingHypo);
    }
  };

  const handleSelectEvidence = (evidenceId: string) => {
    setActiveEvidenceId(evidenceId);
    // Switch to evidence view on mobile if needed
    setMobileTab("evidence");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return { text: "Completed", bg: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" };
      case "partial":
        return { text: "Partial (Syntax Defect)", bg: "bg-amber-500/15 text-amber-400 border-amber-500/30" };
      case "failed":
        return { text: "Failed", bg: "bg-rose-500/15 text-rose-400 border-rose-500/30" };
      default:
        return { text: status, bg: "bg-slate-800 text-slate-400 border-slate-700" };
    }
  };

  const statusBadge = getStatusBadge(report.status);

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] space-y-3">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-[#0d1424] px-5 py-3.5 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-500/30 font-bold text-cyan-400 font-mono text-sm">
            Ω
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold text-slate-100 tracking-tight">
                {report.repository_name}
              </h1>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${statusBadge.bg}`}>
                {statusBadge.text}
              </span>
              {report.abstention_reason && (
                <span className="rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 text-[10px] font-semibold">
                  Abstained
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono truncate max-w-xl">
              Run: {report.run_id} • Source: {report.source_type} • Completed in {(report.duration_ms / 1000).toFixed(2)}s
            </p>
          </div>
        </div>

        {/* Actions & Deliverable link */}
        <div className="flex items-center space-x-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 transition-colors"
            >
              Refresh
            </button>
          )}

          <Link
            href={`/reports/${report.run_id}`}
            className="flex items-center space-x-1.5 rounded-lg border border-cyan-500/40 bg-cyan-950/40 hover:bg-cyan-900/50 text-cyan-300 px-3 py-1.5 text-xs font-semibold transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>View Full Report</span>
          </Link>
        </div>
      </div>

      {/* Mobile Tab Selector */}
      <div className="lg:hidden flex items-center rounded-lg border border-slate-800 bg-[#0d1424] p-1 text-xs shrink-0">
        <button
          onClick={() => setMobileTab("map")}
          className={`flex-1 py-1.5 rounded font-medium transition-colors ${
            mobileTab === "map" ? "bg-cyan-500 text-slate-950 font-bold" : "text-slate-400"
          }`}
        >
          System Map
        </button>
        <button
          onClick={() => setMobileTab("investigation")}
          className={`flex-1 py-1.5 rounded font-medium transition-colors ${
            mobileTab === "investigation" ? "bg-cyan-500 text-slate-950 font-bold" : "text-slate-400"
          }`}
        >
          Investigation &amp; Hypotheses
        </button>
        <button
          onClick={() => setMobileTab("evidence")}
          className={`flex-1 py-1.5 rounded font-medium transition-colors ${
            mobileTab === "evidence" ? "bg-cyan-500 text-slate-950 font-bold" : "text-slate-400"
          }`}
        >
          Evidence Inspector
        </button>
      </div>

      {/* Three-Panel Investigation Layout */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left Panel: System Map (4 cols on desktop) */}
        <div className={`h-full lg:col-span-4 ${mobileTab === "map" ? "block" : "hidden lg:block"}`}>
          <InteractiveSystemMap
            systemMap={report.system_map}
            highlightedComponentId={highlightedComponentId}
            onSelectComponent={handleSelectComponent}
          />
        </div>

        {/* Center Panel: Investigation & Hypotheses (5 cols on desktop) */}
        <div className={`h-full lg:col-span-5 ${mobileTab === "investigation" ? "block" : "hidden lg:block"}`}>
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

        {/* Right Panel: Evidence Inspector (3 cols on desktop) */}
        <div className={`h-full lg:col-span-3 ${mobileTab === "evidence" ? "block" : "hidden lg:block"}`}>
          <EvidenceInspector
            evidenceList={report.evidence}
            activeEvidenceId={activeEvidenceId}
            supportingEvidenceIds={activeHypothesis?.supporting_evidence_ids}
            contradictingEvidenceIds={activeHypothesis?.contradicting_evidence_ids}
            onSelectEvidence={setActiveEvidenceId}
          />
        </div>
      </div>
    </div>
  );
}
