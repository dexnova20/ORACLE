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
  candidateProbes = [],
  executedProbes = [],
  investigationHistory = [],
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

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case "high":
        return { text: "High Confidence", bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" };
      case "medium":
        return { text: "Medium Confidence", bg: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" };
      case "low":
        return { text: "Low Confidence", bg: "bg-slate-800 text-slate-400 border-slate-700" };
      case "uncertain":
      default:
        return { text: "Uncertain", bg: "bg-amber-500/10 text-amber-400 border-amber-500/30" };
    }
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case "verified":
        return { text: "Verified", bg: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" };
      case "partially_verified":
        return { text: "Partially Verified", bg: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40" };
      case "blocked":
        return { text: "Blocked", bg: "bg-rose-500/20 text-rose-300 border-rose-500/40" };
      case "unsupported":
        return { text: "Unsupported", bg: "bg-slate-800 text-slate-400 border-slate-700" };
      default:
        return { text: "Candidate", bg: "bg-violet-500/15 text-violet-300 border-violet-500/30" };
    }
  };

  return (
    <div className="flex flex-col h-full rounded-xl border border-slate-800/80 bg-[#0a0f1d] overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800/80 px-4 py-3 bg-[#0d1322]/80 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-cyan-500/10 text-cyan-400">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Investigation &amp; Fault Hypotheses
            </h2>
            <span className="text-[10px] text-slate-400">
              Select any hypothesis to trace supporting evidence &amp; affected systems
            </span>
          </div>
        </div>

        {stoppingReason && (
          <span className="rounded bg-slate-800/90 border border-slate-700 px-2 py-0.5 font-mono text-[10px] text-cyan-300">
            Stop: {stoppingReason.replace(/_/g, " ")}
          </span>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {hypotheses.length === 0 ? (
          <div className="rounded-xl border border-dashed border-emerald-500/40 bg-emerald-950/15 p-8 text-center space-y-2">
            <div className="h-9 w-9 rounded-full bg-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center font-bold">
              ✓
            </div>
            <h3 className="font-bold text-sm text-emerald-300">
              Clean Control Baseline
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              No causal fault hypotheses were generated. All discovered files parsed without syntax errors, module imports resolved successfully, and no runtime telemetry anomalies were identified.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {hypotheses.map((hypo, idx) => {
              const isSelected = hypo.hypothesis_id === selectedHypoId;
              const confBadge = getConfidenceBadge(hypo.confidence_level);
              const verBadge = getVerificationBadge(hypo.verification_status);
              const matchingVerifications = verificationList.filter(
                (v) => v.hypothesis_id === hypo.hypothesis_id
              );
              const matchingProbes = candidateProbes.filter(
                (p) =>
                  p.target_hypothesis_ids?.includes(hypo.hypothesis_id) ||
                  p.target_component === hypo.affected_component
              );

              return (
                <div
                  key={hypo.hypothesis_id}
                  className={`rounded-xl border transition-all ${
                    isSelected
                      ? "border-cyan-500 bg-[#0d1629] shadow-[0_0_20px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/40"
                      : "border-slate-800 bg-[#0c1220] hover:border-slate-700"
                  }`}
                >
                  {/* Card Summary Header (Clickable) */}
                  <button
                    onClick={() => handleHypothesisClick(hypo)}
                    className="w-full text-left p-4 cursor-pointer focus:outline-none"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-slate-500">
                          #{idx + 1}
                        </span>
                        <span className="font-mono text-xs font-bold text-cyan-300">
                          {hypo.hypothesis_id}
                        </span>
                        <span className="font-bold text-sm text-slate-100">
                          {hypo.category_title}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${confBadge.bg}`}>
                          {confBadge.text}
                        </span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${verBadge.bg}`}>
                          {verBadge.text}
                        </span>
                      </div>
                    </div>

                    {/* Metadata line */}
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-mono">
                      <div>
                        <span className="text-slate-500">Component: </span>
                        <span className="text-cyan-400 font-semibold">{hypo.affected_component}</span>
                      </div>
                      {hypo.relative_ranking_score !== undefined && (
                        <div>
                          <span className="text-slate-500">Score: </span>
                          <span className="text-slate-200">{hypo.relative_ranking_score.toFixed(0)}/100</span>
                        </div>
                      )}
                      <div>
                        <span className="text-slate-500">Evidence: </span>
                        <span className="text-emerald-400 font-semibold">{hypo.supporting_evidence_ids.length} supporting</span>
                        {hypo.contradicting_evidence_ids.length > 0 && (
                          <span className="text-rose-400 ml-1">({hypo.contradicting_evidence_ids.length} contradictory)</span>
                        )}
                      </div>
                    </div>
                  </button>

                  {/* Expanded Signature Explorer Details */}
                  {isSelected && (
                    <div className="border-t border-slate-800/80 p-4 space-y-3.5 bg-[#090e1a]/80 text-xs">
                      {/* Score Rationale */}
                      {hypo.score_rationale && (
                        <div>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1">
                            Diagnostic Rationale:
                          </span>
                          <p className="text-slate-300 leading-relaxed bg-[#0e1526] p-2.5 rounded-lg border border-slate-800">
                            {hypo.score_rationale}
                          </p>
                        </div>
                      )}

                      {/* Evidence Provenance Explorer */}
                      <div>
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1.5">
                          Evidence Provenance Links:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {hypo.supporting_evidence_ids.map((id) => (
                            <button
                              key={id}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onSelectEvidence) onSelectEvidence(id);
                              }}
                              className="inline-flex items-center space-x-1.5 rounded-md border border-emerald-500/40 bg-emerald-950/30 px-2 py-1 font-mono text-[11px] text-emerald-300 hover:bg-emerald-900/40 transition-colors cursor-pointer"
                            >
                              <span>✓</span>
                              <span>{id}</span>
                              <span className="text-[9px] text-emerald-500 font-sans">Inspect →</span>
                            </button>
                          ))}
                          {hypo.contradicting_evidence_ids.map((id) => (
                            <button
                              key={id}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onSelectEvidence) onSelectEvidence(id);
                              }}
                              className="inline-flex items-center space-x-1.5 rounded-md border border-rose-500/40 bg-rose-950/30 px-2 py-1 font-mono text-[11px] text-rose-300 hover:bg-rose-900/40 transition-colors cursor-pointer"
                            >
                              <span>✕</span>
                              <span>{id}</span>
                              <span className="text-[9px] text-rose-500 font-sans">Inspect →</span>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Alternative Explanations & Assumptions */}
                      {hypo.alternative_explanations && hypo.alternative_explanations.length > 0 && (
                        <div>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1">
                            Plausible Confounding Alternatives:
                          </span>
                          <ul className="list-disc list-inside space-y-0.5 text-slate-400 text-[11px]">
                            {hypo.alternative_explanations.map((alt, i) => (
                              <li key={i}>{alt}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Associated Probes & Verification Outcomes */}
                      {(matchingVerifications.length > 0 || matchingProbes.length > 0) && (
                        <div>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1.5">
                            Associated Probes &amp; Verification Outcomes:
                          </span>
                          <div className="space-y-1.5">
                            {matchingVerifications.map((v, vIdx) => (
                              <div
                                key={`ver-${vIdx}`}
                                className="bg-[#0e1526] p-2 rounded-lg border border-slate-800 flex items-center justify-between text-[11px]"
                              >
                                <div>
                                  <span className="font-mono text-cyan-300 mr-2 font-semibold">{v.method}</span>
                                  <span className="text-slate-400">{v.details}</span>
                                </div>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                    v.status === "verified"
                                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                                      : "bg-slate-800 text-slate-400 border-slate-700"
                                  }`}
                                >
                                  {v.status}
                                </span>
                              </div>
                            ))}
                            {matchingProbes.map((p) => (
                              <div
                                key={p.probe_id}
                                className="bg-[#0e1526] p-2 rounded-lg border border-slate-800 flex items-center justify-between text-[11px]"
                              >
                                <div>
                                  <span className="font-mono text-violet-300 mr-2 font-semibold">{p.probe_id}</span>
                                  <span className="text-slate-400">
                                    {p.probe_type} • target: {p.target_component}
                                  </span>
                                </div>
                                <span className="font-mono text-[10px] text-slate-500">
                                  {p.cost_label} | {p.safety_classification}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Recommended Remediation or Next Investigation Step */}
                      {hypo.remediation_suggestion && (
                        <div className="rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-3 space-y-1">
                          <span className="text-[10px] uppercase font-bold tracking-wider text-cyan-400 flex items-center space-x-1.5">
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>Recommended Next Step / Remediation:</span>
                          </span>
                          <p className="text-cyan-200 text-xs font-medium">
                            {hypo.remediation_suggestion}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Decisions / Stopping Rationale */}
      <div className="border-t border-slate-800/80 px-4 py-2 bg-[#090e1a] text-[11px] text-slate-400 flex items-center justify-between font-mono shrink-0">
        <span>Hypotheses: {hypotheses.length}</span>
        <span>Probes Executed: {executedProbes.length}</span>
        <span>Decisions: {investigationHistory.length}</span>
      </div>
    </div>
  );
}
