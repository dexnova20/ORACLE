"use client";

import React from "react";
import {
  DiagnosticDecisionRecord,
  DiagnosticProbe,
  ProbeResult,
} from "@/types/api";

interface AdaptiveInvestigationPanelProps {
  stoppingReason?: string | null;
  investigationHistory?: DiagnosticDecisionRecord[];
  candidateProbes?: DiagnosticProbe[];
  executedProbes?: ProbeResult[];
}

export function AdaptiveInvestigationPanel({
  stoppingReason,
  investigationHistory = [],
  candidateProbes = [],
  executedProbes = [],
}: AdaptiveInvestigationPanelProps) {
  const getDecisionBadge = (decisionType: string) => {
    switch (decisionType) {
      case "select_probe":
        return "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300";
      case "stop_sufficient_evidence":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "stop_unsafe_unsupported":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
      case "deliberate_abstention":
        return "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300";
      case "stop_budget_exhausted":
      case "stop_no_probes":
      default:
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
    }
  };

  const getSafetyBadge = (classification: string) => {
    switch (classification) {
      case "safe_read_only":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "controlled_dynamic":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
      case "unsupported_unsafe":
      default:
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "executed":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "unsupported":
        return "bg-zinc-200 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300";
      case "skipped_safety":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
      default:
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Summary */}
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-950/50">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Adaptive Investigation Loop
              </span>
              {stoppingReason && (
                <span className="rounded bg-zinc-200 px-2 py-0.5 font-mono text-[10px] font-bold text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
                  {stoppingReason}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
              Evaluates diagnostic uncertainty, selects optimal discriminatory probes using expected information gain or discrimination heuristics, gates against unisolated dynamic execution, and halts cleanly.
            </p>
          </div>
          <div className="flex items-center space-x-4 text-xs">
            <div className="text-center">
              <div className="font-mono text-base font-bold text-zinc-900 dark:text-zinc-100">
                {investigationHistory.length}
              </div>
              <div className="text-[10px] text-zinc-500">Decisions</div>
            </div>
            <div className="text-center">
              <div className="font-mono text-base font-bold text-zinc-900 dark:text-zinc-100">
                {executedProbes.length}
              </div>
              <div className="text-[10px] text-zinc-500">Executed</div>
            </div>
            <div className="text-center">
              <div className="font-mono text-base font-bold text-zinc-900 dark:text-zinc-100">
                {candidateProbes.length}
              </div>
              <div className="text-[10px] text-zinc-500">Candidates</div>
            </div>
          </div>
        </div>
      </div>

      {/* Investigation Decision Timeline */}
      <div>
        <div className="flex items-center justify-between border-b border-zinc-200 pb-2 dark:border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Investigation Decision Timeline ({investigationHistory.length})
          </h3>
          <span className="text-[11px] text-zinc-400">
            Sequential bounded planning iterations &amp; stopping decisions
          </span>
        </div>

        <div className="mt-3 space-y-3">
          {investigationHistory.length === 0 ? (
            <div className="text-xs italic text-zinc-400">
              No adaptive decisions recorded for this run.
            </div>
          ) : (
            investigationHistory.map((rec, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 pb-2.5 dark:border-zinc-800">
                  <div className="flex items-center space-x-2">
                    <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                      Iteration {rec.iteration}
                    </span>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-semibold ${getDecisionBadge(
                        rec.decision_type
                      )}`}
                    >
                      {rec.decision_type}
                    </span>
                    {rec.selected_probe_id && (
                      <span className="font-mono text-xs font-semibold text-blue-600 dark:text-blue-400">
                        → {rec.selected_probe_id}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] text-zinc-400">
                      {rec.candidates_considered_count} candidate(s) evaluated
                    </span>
                    <span className="font-mono text-[10px] text-zinc-400">
                      {new Date(rec.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <div className="mt-2.5 space-y-1.5 text-xs">
                  <div>
                    <span className="font-medium text-zinc-500">Rationale:</span>{" "}
                    <span className="text-zinc-800 dark:text-zinc-200">{rec.rationale}</span>
                  </div>
                  {rec.remaining_uncertainty && (
                    <div>
                      <span className="font-medium text-zinc-500">Uncertainty State:</span>{" "}
                      <span className="text-[11px] text-zinc-600 dark:text-zinc-400">
                        {rec.remaining_uncertainty}
                      </span>
                    </div>
                  )}
                  {rec.stopping_reason && (
                    <div className="mt-1 rounded bg-zinc-50 px-2 py-1 text-[11px] text-zinc-700 dark:bg-zinc-950 dark:text-zinc-300">
                      <span className="font-semibold">Stopping Condition:</span> {rec.stopping_reason}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Executed Probes */}
      <div>
        <div className="flex items-center justify-between border-b border-zinc-200 pb-2 dark:border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Executed Probes ({executedProbes.length})
          </h3>
          <span className="text-[11px] text-zinc-400">
            Probes actually dispatched through safe adapters
          </span>
        </div>

        <div className="mt-3 space-y-3">
          {executedProbes.length === 0 ? (
            <div className="text-xs italic text-zinc-400">No probes executed during this run.</div>
          ) : (
            executedProbes.map((probe, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-zinc-200 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/40"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200/60 pb-2 dark:border-zinc-800">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      {probe.probe_id}
                    </span>
                    <span className="rounded bg-zinc-200 px-1.5 py-0.5 font-mono text-[10px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                      {probe.probe_type}
                    </span>
                    <span className="font-mono text-xs text-zinc-600 dark:text-zinc-400">
                      [{probe.target_component}]
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-semibold ${getStatusBadge(
                        probe.execution_status
                      )}`}
                    >
                      {probe.execution_status}
                    </span>
                    {probe.ranking_changed && (
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                        Ranking Updated
                      </span>
                    )}
                    <span className="font-mono text-[10px] text-zinc-400">
                      {probe.duration_ms.toFixed(1)}ms
                    </span>
                  </div>
                </div>

                <div className="mt-2.5 space-y-1.5 text-xs">
                  <div>
                    <span className="font-medium text-zinc-500">Outcome:</span>{" "}
                    <span className="font-mono text-[11px] font-semibold text-zinc-800 dark:text-zinc-200">
                      {probe.outcome}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 text-[11px] text-zinc-500">
                    <span>
                      Safety Policy:{" "}
                      <code className="rounded bg-zinc-100 px-1 py-0.5 dark:bg-zinc-800">
                        {probe.applied_safety_policy}
                      </code>
                    </span>
                    {probe.generated_evidence_ids.length > 0 && (
                      <span>
                        Generated Evidence:{" "}
                        {probe.generated_evidence_ids.map((id) => (
                          <span
                            key={id}
                            className="mr-1 rounded bg-amber-50 px-1.5 py-0.2 font-mono text-[10px] font-semibold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                          >
                            {id}
                          </span>
                        ))}
                      </span>
                    )}
                  </div>
                  {probe.unsupported_reason && (
                    <div className="rounded bg-rose-50/80 p-2 text-[11px] text-rose-800 dark:bg-rose-950/40 dark:text-rose-300">
                      <span className="font-semibold">Unsupported / Safety Halt:</span>{" "}
                      {probe.unsupported_reason}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Candidate Probes Pool */}
      {candidateProbes.length > 0 && (
        <div>
          <div className="flex items-center justify-between border-b border-zinc-200 pb-2 dark:border-zinc-800">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Candidate Diagnostic Probes ({candidateProbes.length})
            </h3>
            <span className="text-[11px] text-zinc-400">
              Generated candidate actions evaluated by probe planner
            </span>
          </div>

          <div className="mt-3 space-y-2">
            {candidateProbes.map((cp) => (
              <div
                key={cp.probe_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-zinc-200 bg-white p-3 text-xs shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      {cp.probe_id}
                    </span>
                    <span className="font-mono text-[10px] text-zinc-500">{cp.probe_type}</span>
                    <span className="font-mono text-[10px] text-zinc-400">
                      target: {cp.target_component}
                    </span>
                  </div>
                  {cp.selection_reason && (
                    <div className="mt-1 text-[11px] text-emerald-700 dark:text-emerald-400">
                      ✓ {cp.selection_reason}
                    </div>
                  )}
                  {cp.rejection_reason && (
                    <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
                      ⊘ {cp.rejection_reason}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${getSafetyBadge(
                      cp.safety_classification
                    )}`}
                  >
                    {cp.safety_classification}
                  </span>
                  <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[9px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                    cost: {cp.cost_label} ({cp.estimated_cost})
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                      cp.availability_status === "available"
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                        : "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300"
                    }`}
                  >
                    {cp.availability_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
