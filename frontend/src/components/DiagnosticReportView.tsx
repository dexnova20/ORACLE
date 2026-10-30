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
        return { label: "Verified", badge: "bg-[#D4FF32]/20 text-[#D4FF32] border-[#D4FF32]/50 font-bold" };
      case "partially_verified":
        return { label: "Partially Verified", badge: "bg-[#D4FF32]/10 text-[#D4FF32] border-[#D4FF32]/30 font-bold" };
      case "blocked":
        return { label: "Blocked", badge: "bg-[#F20B91]/20 text-[#F20B91] border-[#F20B91]/50 font-bold" };
      case "unsupported":
        return { label: "Unsupported", badge: "bg-black/50 text-[#85858D] border-white/[0.08]" };
      case "not_verified":
      default:
        return { label: "Candidate", badge: "bg-white/[0.05] text-[#F5F3EF] border-white/[0.1]" };
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16 font-sans">
      {/* Editorial Report Header */}
      <div className="rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-xs font-mono">
              <span className="font-black text-[#D4FF32] uppercase tracking-widest">
                DIAGNOSTIC DELIVERABLE REPORT
              </span>
              <span className="text-[#85858D]">•</span>
              <span className="text-[#85858D]">{report.run_id}</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-[#F5F3EF] tracking-tight uppercase">
              {report.repository_name}
            </h1>
          </div>

          <div className="flex items-center space-x-2 font-mono text-xs">
            <span
              className={`rounded border px-2.5 py-1 text-[11px] font-black uppercase tracking-wider ${
                report.status === "completed"
                  ? "border-[#D4FF32]/50 bg-black text-[#D4FF32]"
                  : report.status === "partial"
                  ? "border-[#D4FF32]/30 bg-black text-[#D4FF32]"
                  : "border-[#F20B91]/50 bg-black text-[#F20B91]"
                }`}
            >
              Status: {report.status}
            </span>

            <Link
              href="/workspace"
              className="rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-3.5 py-1.5 transition-colors"
            >
              Open Workspace →
            </Link>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="space-y-2">
          <h2 className="text-[10px] font-mono font-black uppercase tracking-widest text-[#85858D]">
            Executive Summary
          </h2>
          <p className="text-sm text-[#F5F3EF] leading-relaxed bg-[#09090B] p-4 rounded border border-white/[0.06]">
            {report.summary ||
              "The diagnostic pipeline completed polyglot static inspection and evidence aggregation across the target repository."}
          </p>
          {report.abstention_reason && (
            <div className="rounded border border-[#F20B91]/40 bg-black/60 p-3.5 text-xs text-[#F20B91] space-y-1 font-mono font-bold">
              <span className="block text-[#F20B91]">
                Deliberate Abstention Notice:
              </span>
              <p className="font-sans font-normal text-[#F5F3EF]">{report.abstention_reason}</p>
            </div>
          )}
        </div>

        {/* Diagnostic Metadata Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
          <div className="rounded bg-[#09090B] p-3 border border-white/[0.06]">
            <span className="text-[#85858D] block text-[10px] font-bold uppercase">Source Type:</span>
            <span className="text-[#F5F3EF] font-bold">{report.source_type}</span>
          </div>
          <div className="rounded bg-[#09090B] p-3 border border-white/[0.06]">
            <span className="text-[#85858D] block text-[10px] font-bold uppercase">Duration:</span>
            <span className="text-[#F5F3EF] font-bold">{(report.duration_ms / 1000).toFixed(2)}s</span>
          </div>
          <div className="rounded bg-[#09090B] p-3 border border-white/[0.06]">
            <span className="text-[#85858D] block text-[10px] font-bold uppercase">Hypotheses:</span>
            <span className="text-[#D4FF32] font-black">{report.hypotheses.length} ranked</span>
          </div>
          <div className="rounded bg-[#09090B] p-3 border border-white/[0.06]">
            <span className="text-[#85858D] block text-[10px] font-bold uppercase">Evidence Tokens:</span>
            <span className="text-[#D4FF32] font-black">{report.evidence.length} records</span>
          </div>
        </div>
      </div>

      {/* Ranked Hypotheses Section */}
      <div className="rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-8 space-y-4">
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
          <h2 className="text-sm font-mono font-black uppercase tracking-widest text-[#F5F3EF]">
            Ranked Causal Hypotheses
          </h2>
          <span className="text-xs font-mono text-[#85858D]">
            Prioritized by ML Information Gain
          </span>
        </div>

        {report.hypotheses.length === 0 ? (
          <div className="rounded border border-dashed border-[#D4FF32]/40 bg-[#09090B] p-6 text-center text-xs font-mono text-[#85858D]">
            No causal fault hypotheses generated. Codebase verified clean.
          </div>
        ) : (
          <div className="space-y-4">
            {report.hypotheses.map((hypo, idx) => {
              const statusInfo = getStatusLabel(hypo.verification_status);

              return (
                <div
                  key={hypo.hypothesis_id}
                  className="rounded border border-white/[0.08] bg-[#09090B] p-4 space-y-3 font-mono"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2 text-[11px]">
                        <span className="font-black text-[#F20B91]">
                          #{idx + 1}
                        </span>
                        <span className="text-[#85858D]">•</span>
                        <span className="text-[#85858D]">{hypo.hypothesis_id}</span>
                        <span className="text-[#85858D]">•</span>
                        <span className="text-[#D4FF32] font-bold">{hypo.affected_component}</span>
                      </div>
                      <h3 className="font-sans font-bold text-sm text-[#F5F3EF]">
                        {hypo.category_title}
                      </h3>
                    </div>

                    <div className="flex items-center space-x-2 text-[10px]">
                      <span className={`px-2 py-0.5 rounded border uppercase ${statusInfo.badge}`}>
                        {statusInfo.label}
                      </span>
                      {hypo.relative_ranking_score !== undefined && hypo.relative_ranking_score !== null && (
                        <span className="font-black text-xs text-[#D4FF32] bg-black px-2 py-0.5 rounded border border-[#D4FF32]/30">
                          Score: {(hypo.relative_ranking_score * 100).toFixed(0)}
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="font-sans text-xs text-[#F5F3EF] leading-relaxed">
                    {hypo.score_rationale || hypo.remediation_suggestion || hypo.category_title}
                  </p>

                  {/* Supporting / Contradicting Evidence References */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[10px]">
                    {hypo.supporting_evidence_ids.length > 0 && (
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[#D4FF32] font-black uppercase">Supporting:</span>
                        {hypo.supporting_evidence_ids.map((id) => (
                          <span
                            key={id}
                            className="rounded border border-[#D4FF32]/40 bg-[#151519] px-1.5 py-0.5 text-[#D4FF32] font-bold"
                          >
                            + {id}
                          </span>
                        ))}
                      </div>
                    )}
                    {hypo.contradicting_evidence_ids.length > 0 && (
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[#F20B91] font-black uppercase">Contradictory:</span>
                        {hypo.contradicting_evidence_ids.map((id) => (
                          <span
                            key={id}
                            className="rounded border border-[#F20B91]/40 bg-[#151519] px-1.5 py-0.5 text-[#F20B91] font-bold"
                          >
                            - {id}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Uncertainty Notice & Diagnostic Boundaries */}
      <div className="rounded border border-white/[0.08] bg-[#151519] p-6 space-y-2 font-mono text-xs">
        <span className="text-[10px] font-black uppercase tracking-widest text-[#F20B91] block">
          Diagnostic Boundaries &amp; Integrity Notice
        </span>
        <p className="text-[11px] text-[#85858D] font-sans leading-relaxed">
          ORACLE results reflect observable static AST syntax trees, dependency linkages, and submitted execution telemetry. Components not covered by registered source files or skipped due to container isolation gating are excluded from causal attribution.
        </p>
      </div>
    </div>
  );
}
