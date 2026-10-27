"use client";

import React from "react";
import Link from "next/link";
import { DiagnosticReport } from "@/types/api";

interface DiagnosticReportViewProps {
  report: DiagnosticReport;
}

export function DiagnosticReportView({ report }: DiagnosticReportViewProps) {
  const getStatusLabel = (status: string) => {
    switch (status) {
      case "verified":
        return { label: "Verified", badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" };
      case "partially_verified":
      case "supported":
        return { label: "Supported by Evidence", badge: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40" };
      case "candidate":
        return { label: "Hypothesis", badge: "bg-violet-500/20 text-violet-300 border-violet-500/40" };
      case "blocked":
        return { label: "Blocked", badge: "bg-rose-500/20 text-rose-300 border-rose-500/40" };
      case "untested":
        return { label: "Untested", badge: "bg-slate-800 text-slate-400 border-slate-700" };
      case "unsupported":
        return { label: "Unsupported", badge: "bg-zinc-800 text-zinc-400 border-zinc-700" };
      case "uncertain":
      default:
        return { label: "Uncertain", badge: "bg-amber-500/20 text-amber-300 border-amber-500/40" };
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header & Meta Bar */}
      <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs uppercase tracking-wider text-cyan-400 font-bold">
                Diagnostic Deliverable Report
              </span>
              <span className="text-slate-600">•</span>
              <span className="font-mono text-xs text-slate-400">{report.run_id}</span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">
              {report.repository_name}
            </h1>
          </div>

          <div className="flex items-center space-x-2">
            <span
              className={`rounded-lg border px-3 py-1 font-mono text-xs font-bold uppercase tracking-wider ${
                report.status === "completed"
                  ? "border-emerald-500/40 bg-emerald-950/30 text-emerald-400"
                  : report.status === "partial"
                  ? "border-amber-500/40 bg-amber-950/30 text-amber-400"
                  : "border-rose-500/40 bg-rose-950/30 text-rose-400"
              }`}
            >
              Status: {report.status}
            </span>

            <Link
              href="/workspace"
              className="rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 px-3 py-1 text-xs text-slate-200 transition-colors"
            >
              Open Workspace →
            </Link>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="space-y-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Executive Summary
          </h2>
          <p className="text-sm text-slate-200 leading-relaxed bg-[#080d19] p-4 rounded-lg border border-slate-800 font-sans">
            {report.summary ||
              "The diagnostic pipeline completed polyglot static inspection and evidence aggregation across the target repository."}
          </p>
          {report.abstention_reason && (
            <div className="rounded-lg border border-purple-900/60 bg-purple-950/20 p-3.5 text-xs text-purple-200 space-y-1">
              <span className="font-bold block text-purple-300">
                Deliberate Abstention Notice:
              </span>
              <p>{report.abstention_reason}</p>
            </div>
          )}
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs font-mono">
          <div className="rounded-lg bg-[#080d19] p-2.5 border border-slate-800/60">
            <span className="text-slate-500 block text-[10px]">Source Type:</span>
            <span className="text-slate-200 font-semibold">{report.source_type}</span>
          </div>
          <div className="rounded-lg bg-[#080d19] p-2.5 border border-slate-800/60">
            <span className="text-slate-500 block text-[10px]">Duration:</span>
            <span className="text-slate-200 font-semibold">{(report.duration_ms / 1000).toFixed(2)}s</span>
          </div>
          <div className="rounded-lg bg-[#080d19] p-2.5 border border-slate-800/60">
            <span className="text-slate-500 block text-[10px]">Stages Run:</span>
            <span className="text-emerald-400 font-semibold">{report.completed_stages.length}</span>
          </div>
          <div className="rounded-lg bg-[#080d19] p-2.5 border border-slate-800/60">
            <span className="text-slate-500 block text-[10px]">Stopping Rationale:</span>
            <span className="text-cyan-300 font-semibold truncate block" title={report.stopping_reason || "completed"}>
              {report.stopping_reason || "normal"}
            </span>
          </div>
        </div>
      </div>

      {/* Ranked Fault Hypotheses & Provenance */}
      <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Ranked Fault Hypotheses ({report.hypotheses.length})
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            Evidence-Based Relative Ranking
          </span>
        </div>

        {report.hypotheses.length === 0 ? (
          <div className="rounded-lg border border-dashed border-emerald-500/40 bg-emerald-950/20 p-6 text-center text-xs text-emerald-300">
            No causal fault hypotheses were triggered. Baseline repository confirmed healthy.
          </div>
        ) : (
          <div className="space-y-4">
            {report.hypotheses.map((hypo, i) => {
              const status = getStatusLabel(hypo.verification_status);
              return (
                <div key={hypo.hypothesis_id} className="rounded-lg border border-slate-800 bg-[#080d19] p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/60 pb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-slate-500">#{i + 1}</span>
                      <span className="font-mono text-xs font-bold text-cyan-300">{hypo.hypothesis_id}</span>
                      <h3 className="text-sm font-bold text-slate-100">{hypo.category_title}</h3>
                    </div>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${status.badge}`}>
                      {status.label}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                    <div>
                      <span className="text-slate-500 block text-[10px]">Affected Component:</span>
                      <span className="font-mono text-cyan-300 font-semibold">{hypo.affected_component}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Confidence &amp; Score:</span>
                      <span className="font-mono text-slate-200">
                        {hypo.relative_ranking_score?.toFixed(0) || "N/A"}/100 ({hypo.confidence_level})
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Supporting Evidence:</span>
                      <span className="font-mono text-emerald-400">
                        {hypo.supporting_evidence_ids.join(", ") || "None"}
                      </span>
                    </div>
                  </div>

                  {hypo.score_rationale && (
                    <p className="text-xs text-slate-300 bg-[#0d1424] p-2.5 rounded border border-slate-800/80">
                      {hypo.score_rationale}
                    </p>
                  )}

                  {hypo.remediation_suggestion && (
                    <div className="rounded border border-cyan-500/20 bg-cyan-950/20 p-2.5 text-xs text-cyan-200">
                      <span className="font-bold text-cyan-400 block mb-0.5">Recommended Next Action:</span>
                      {hypo.remediation_suggestion}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Verification Outcomes & Diagnostic Probes */}
      {report.verification && report.verification.length > 0 && (
        <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 border-b border-slate-800/80 pb-3">
            Verification Results &amp; Probes ({report.verification.length})
          </h2>
          <div className="space-y-2">
            {report.verification.map((v, i) => {
              const status = getStatusLabel(v.status);
              return (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-[#080d19] text-xs">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-300">{v.hypothesis_id}</span>
                      <span className="text-slate-500">via {v.method}</span>
                    </div>
                    <p className="text-slate-400 text-[11px]">{v.details}</p>
                  </div>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border shrink-0 ${status.badge}`}>
                    {status.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Diagnostic Limitations & Remaining Uncertainties */}
      <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 border-b border-slate-800/80 pb-2">
          Diagnostic Boundaries &amp; Remaining Uncertainties
        </h2>
        <ul className="list-disc list-inside text-xs text-slate-400 space-y-1 leading-relaxed">
          <li>
            Analysis was performed strictly using verified static AST inspectors and captured telemetry without executing uncontained code on the host.
          </li>
          {report.unsupported_stages.length > 0 && (
            <li className="text-amber-300">
              Unsupported stages in this environment: {report.unsupported_stages.join(", ")}
            </li>
          )}
          <li>
            Dynamic containerized execution requires an active Docker daemon. When unavailable, dynamic verification halts safely to prevent host compromise.
          </li>
        </ul>
      </div>
    </div>
  );
}
