"use client";

import React from "react";
import { FaultHypothesis, VerificationOutcome } from "@/types/api";

interface HypothesisPanelProps {
  hypotheses: FaultHypothesis[];
  verificationList: VerificationOutcome[];
  onSelectEvidence?: (evidenceId: string) => void;
}

export function HypothesisPanel({
  hypotheses,
  verificationList,
  onSelectEvidence,
}: HypothesisPanelProps) {
  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case "high":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "medium":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
      case "low":
        return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
      case "uncertain":
      default:
        return "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300";
    }
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case "verified":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "partially_verified":
        return "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300";
      case "unsupported":
        return "bg-zinc-200 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300";
      case "blocked":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
      default:
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
    }
  };

  return (
    <div className="space-y-6">
      {/* Hypotheses List */}
      <div>
        <div className="flex items-center justify-between border-b border-zinc-200 pb-2 dark:border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Causal Fault Hypotheses ({hypotheses.length})
          </h3>
          <span className="text-[11px] text-zinc-400">
            Derived from empirical static &amp; dynamic evidence without benchmark leakage
          </span>
        </div>

        <div className="mt-3 space-y-4">
          {hypotheses.length === 0 ? (
            <div className="rounded-lg border border-dashed border-emerald-300 bg-emerald-50/40 p-6 text-center text-xs text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/20 dark:text-emerald-300">
              <span className="font-semibold">Clean Baseline Target:</span> No fault hypotheses were generated. Codebase passed syntax analysis and module resolution.
            </div>
          ) : (
            hypotheses.map((hypo, idx) => (
              <div
                key={hypo.hypothesis_id}
                className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 pb-3 dark:border-zinc-800">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-zinc-400">#{idx + 1}</span>
                    <span className="font-mono text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      {hypo.hypothesis_id}
                    </span>
                    <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                      {hypo.category_title}
                    </h4>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] text-zinc-500">{hypo.category}</span>
                    <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${getConfidenceBadge(hypo.confidence_level)}`}>
                      Confidence: {hypo.confidence_level}
                    </span>
                    <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${getVerificationBadge(hypo.verification_status)}`}>
                      {hypo.verification_status}
                    </span>
                  </div>
                </div>

                <div className="mt-3 space-y-3 text-xs">
                  {hypo.relative_ranking_score !== undefined && (
                    <div className="flex flex-wrap items-center gap-2 rounded bg-zinc-100/70 px-2.5 py-1.5 dark:bg-zinc-800/50">
                      <span className="font-mono text-xs font-bold text-zinc-900 dark:text-zinc-100">
                        Score: {hypo.relative_ranking_score.toFixed(1)}/100
                      </span>
                      <span className="text-[10px] text-zinc-500">
                        (Relative heuristic ranking score &mdash; NOT calibrated probability)
                      </span>
                    </div>
                  )}

                  {hypo.score_rationale && (
                    <div className="rounded-md bg-zinc-50 p-2.5 text-zinc-700 dark:bg-zinc-950/60 dark:text-zinc-300 border border-zinc-100 dark:border-zinc-800">
                      <div className="font-semibold text-[11px] text-zinc-500 mb-0.5">Scoring Rationale:</div>
                      <div className="text-[11px] font-mono leading-relaxed">{hypo.score_rationale}</div>
                    </div>
                  )}

                  <div>
                    <span className="font-medium text-zinc-500">Affected Component:</span>{" "}
                    <code className="font-mono font-semibold text-zinc-900 dark:text-zinc-100">
                      {hypo.affected_component}
                    </code>
                  </div>

                  {hypo.assumptions && hypo.assumptions.length > 0 && (
                    <div>
                      <span className="font-medium text-zinc-500">Key Assumptions:</span>
                      <ul className="mt-1 list-disc pl-5 text-[11px] text-zinc-600 dark:text-zinc-400 space-y-0.5">
                        {hypo.assumptions.map((assump, i) => (
                          <li key={i}>{assump}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Supporting Evidence Badges */}
                  <div>
                    <span className="font-medium text-zinc-500">Supporting Evidence:</span>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {hypo.supporting_evidence_ids.length === 0 ? (
                        <span className="text-[11px] text-zinc-400 italic">None referenced</span>
                      ) : (
                        hypo.supporting_evidence_ids.map((eid) => (
                          <button
                            key={eid}
                            onClick={() => onSelectEvidence?.(eid)}
                            className="rounded border border-amber-300 bg-amber-50 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber-900 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                          >
                            🔗 {eid}
                          </button>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Alternative Explanations */}
                  {hypo.alternative_explanations.length > 0 && (
                    <div>
                      <span className="font-medium text-zinc-500">Plausible Alternative Explanations:</span>
                      <ul className="mt-1 list-disc pl-5 text-[11px] text-zinc-600 dark:text-zinc-400 space-y-0.5">
                        {hypo.alternative_explanations.map((alt, i) => (
                          <li key={i}>{alt}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Remediation */}
                  {hypo.remediation_suggestion && (
                    <div className="rounded-md bg-blue-50/70 p-3 text-blue-900 dark:bg-blue-950/30 dark:text-blue-200">
                      <div className="font-semibold text-[11px] mb-0.5">Recommended Next Action:</div>
                      <div className="text-[11px] leading-relaxed">{hypo.remediation_suggestion}</div>
                    </div>
                  )}

                  {/* Explicit Abstention Reason */}
                  {hypo.abstention_reason && (
                    <div className="rounded-md bg-purple-50/70 p-3 text-purple-900 dark:bg-purple-950/30 dark:text-purple-200">
                      <div className="font-semibold text-[11px] mb-0.5">Abstention Notice:</div>
                      <div className="text-[11px] leading-relaxed">{hypo.abstention_reason}</div>
                    </div>
                  )}

                  {/* Explicit Uncertainty Reason */}
                  {hypo.uncertainty_reason && (
                    <div className="rounded-md bg-amber-50/70 p-3 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200 border border-amber-200/60 dark:border-amber-900/40">
                      <div className="font-semibold text-[11px] mb-0.5">Uncertainty Reason:</div>
                      <div className="text-[11px] leading-relaxed">{hypo.uncertainty_reason}</div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Verification Outcomes */}
      <div>
        <div className="flex items-center justify-between border-b border-zinc-200 pb-2 dark:border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Verification Attempts &amp; Outcomes ({verificationList.length})
          </h3>
          <span className="text-[11px] text-zinc-400">
            Independent checks (AST validation / Isolated container preflight)
          </span>
        </div>

        <div className="mt-3 space-y-2">
          {verificationList.length === 0 ? (
            <div className="text-xs text-zinc-400 italic">No verification attempts recorded.</div>
          ) : (
            verificationList.map((ver, idx) => (
              <div
                key={idx}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-950/50"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[11px] font-semibold text-zinc-800 dark:text-zinc-200">
                      target: {ver.hypothesis_id}
                    </span>
                    <span className="font-mono text-[10px] text-zinc-500">
                      via {ver.method}
                    </span>
                    {ver.workload_profile && (
                      <span className="rounded bg-zinc-200/70 px-1.5 py-0.2 text-[9px] font-mono text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                        {ver.workload_profile}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-[11px] text-zinc-600 dark:text-zinc-400">
                    {ver.details}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {ver.exit_code !== null && ver.exit_code !== undefined && (
                    <span className="font-mono text-[10px] text-zinc-400">
                      exit: {ver.exit_code}
                    </span>
                  )}
                  <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${getVerificationBadge(ver.status)}`}>
                    {ver.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
