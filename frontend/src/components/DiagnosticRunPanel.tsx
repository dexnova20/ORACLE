"use client";

import React, { useState, useEffect } from "react";
import { getLatestDiagnosticReport, startDiagnosticRun } from "@/lib/api";
import { DiagnosticReport, Repository } from "@/types/api";
import { AdaptiveInvestigationPanel } from "./AdaptiveInvestigationPanel";
import { DiagnosticReportSummary } from "./DiagnosticReportSummary";
import { EvidencePanel } from "./EvidencePanel";
import { HypothesisPanel } from "./HypothesisPanel";
import { SystemMapViewer } from "./SystemMapViewer";

interface DiagnosticRunPanelProps {
  repositories: Repository[];
}

type TabType = "summary" | "investigation" | "map" | "hypotheses" | "evidence";

export function DiagnosticRunPanel({ repositories }: DiagnosticRunPanelProps) {
  const [customRepoId, setCustomRepoId] = useState<string>("");
  const [allowDynamic, setAllowDynamic] = useState<boolean>(false);
  const [symptomText, setSymptomText] = useState<string>("");
  const [tracebackText, setTracebackText] = useState<string>("");
  const [showRuntimeContext, setShowRuntimeContext] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<TabType>("summary");
  const [highlightedEvidenceId, setHighlightedEvidenceId] = useState<string | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<DiagnosticReport | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Derive effective selected repo without setState inside effect
  const effectiveRepoId = customRepoId || (repositories.length > 0 ? repositories[0].id : "");

  // Load latest report when target repo changes
  useEffect(() => {
    if (!effectiveRepoId) return;

    let isMounted = true;
    getLatestDiagnosticReport(effectiveRepoId)
      .then((data) => {
        if (isMounted) {
          setReport(data);
          setErrorMessage(null);
        }
      })
      .catch(() => {
        // No report exists yet for this repo, which is expected before first run
        if (isMounted) {
          setReport(null);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [effectiveRepoId]);

  const handleStartDiagnosis = async () => {
    if (!effectiveRepoId || loading) return;

    setLoading(true);
    setErrorMessage(null);

    try {
      const result = await startDiagnosticRun(effectiveRepoId, {
        allow_dynamic: allowDynamic,
        symptom_description: symptomText.trim() || undefined,
        runtime_traceback: tracebackText.trim() || undefined,
      });
      setReport(result);
      setActiveTab("summary");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute diagnostic run.";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEvidenceFromHypothesis = (evidenceId: string) => {
    setHighlightedEvidenceId(evidenceId);
    setActiveTab("evidence");
    setTimeout(() => {
      const el = document.getElementById(`evidence-${evidenceId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
  };

  const selectedRepo = repositories.find((r) => r.id === effectiveRepoId);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-zinc-100 pb-4 dark:border-zinc-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              End-to-End Diagnostic Pipeline
            </h2>
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
              Live Engine Active
            </span>
          </div>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Execute safe ingestion, static inspection, component mapping, and causal diagnosis against registered targets.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={effectiveRepoId}
            onChange={(e) => setCustomRepoId(e.target.value)}
            disabled={loading || repositories.length === 0}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 transition-colors focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            {repositories.length === 0 ? (
              <option value="">No targets registered</option>
            ) : (
              repositories.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.source_type})
                </option>
              ))
            )}
          </select>

          <button
            onClick={handleStartDiagnosis}
            disabled={loading || !effectiveRepoId}
            className="inline-flex items-center rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {loading ? (
              <>
                <svg className="mr-2 h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Evaluating Target...
              </>
            ) : (
              <>Initiate Diagnostic Run</>
            )}
          </button>
        </div>
      </div>

      {/* Security Authorization Toggle */}
      <div className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50/60 p-3.5 text-xs dark:border-zinc-800 dark:bg-zinc-950/40">
        <label className="flex items-start space-x-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={allowDynamic}
            onChange={(e) => setAllowDynamic(e.target.checked)}
            disabled={loading}
            className="mt-0.5 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900 dark:border-zinc-700"
          />
          <div>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              Authorize Dynamic Sandbox Execution
            </span>
            <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400">
              When checked, approved containerized workload profiles will execute inside an isolated Docker sandbox. If host isolation is unavailable, dynamic execution will be safely disabled with zero untrusted execution on host.
            </p>
          </div>
        </label>
      </div>

      {/* Runtime Symptom & Traceback Context (Collapsible) */}
      <div className="mb-6 rounded-lg border border-zinc-200 bg-zinc-50/40 p-3.5 text-xs dark:border-zinc-800 dark:bg-zinc-950/20">
        <button
          type="button"
          onClick={() => setShowRuntimeContext(!showRuntimeContext)}
          className="flex w-full items-center justify-between font-semibold text-zinc-900 dark:text-zinc-100 hover:text-zinc-600 dark:hover:text-zinc-300"
        >
          <span className="flex items-center space-x-2">
            <span>Runtime Telemetry &amp; Error Context</span>
            <span className="rounded bg-zinc-200 px-1.5 py-0.2 text-[10px] font-normal text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
              Optional
            </span>
          </span>
          <span className="text-zinc-400">{showRuntimeContext ? "▲ Hide" : "▼ Expand"}</span>
        </button>

        {showRuntimeContext && (
          <div className="mt-3 space-y-3 pt-3 border-t border-zinc-200 dark:border-zinc-800">
            <div>
              <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Observed Symptom or Error Message
              </label>
              <input
                type="text"
                placeholder="e.g. psycopg.OperationalError: connection to server at port 5432 failed"
                value={symptomText}
                onChange={(e) => setSymptomText(e.target.value)}
                disabled={loading}
                className="w-full rounded border border-zinc-300 bg-white p-2 font-mono text-[11px] text-zinc-900 focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Captured Runtime Stack Trace / Panic
              </label>
              <textarea
                rows={3}
                placeholder="Paste Python traceback, Node.js stack trace, Java exception, or Go panic..."
                value={tracebackText}
                onChange={(e) => setTracebackText(e.target.value)}
                disabled={loading}
                className="w-full rounded border border-zinc-300 bg-white p-2 font-mono text-[11px] text-zinc-900 focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              />
            </div>
          </div>
        )}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
          <div className="font-semibold mb-1">Diagnostic Run Error</div>
          <div>{errorMessage}</div>
        </div>
      )}

      {/* Pipeline Navigation Tabs (Visible when Report Available) */}
      {report && (
        <div className="space-y-6">
          <div className="flex border-b border-zinc-200 text-xs font-medium dark:border-zinc-800">
            <button
              onClick={() => setActiveTab("summary")}
              className={`border-b-2 px-4 py-2.5 transition-colors ${
                activeTab === "summary"
                  ? "border-zinc-900 text-zinc-950 dark:border-white dark:text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              Synthesis &amp; Report
            </button>
            <button
              onClick={() => setActiveTab("investigation")}
              className={`border-b-2 px-4 py-2.5 transition-colors ${
                activeTab === "investigation"
                  ? "border-zinc-900 text-zinc-950 dark:border-white dark:text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              Adaptive Investigation ({report.investigation_history?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab("map")}
              className={`border-b-2 px-4 py-2.5 transition-colors ${
                activeTab === "map"
                  ? "border-zinc-900 text-zinc-950 dark:border-white dark:text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              System Map ({report.system_map.total_components})
            </button>
            <button
              onClick={() => setActiveTab("hypotheses")}
              className={`border-b-2 px-4 py-2.5 transition-colors ${
                activeTab === "hypotheses"
                  ? "border-zinc-900 text-zinc-950 dark:border-white dark:text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              Hypotheses &amp; Verification ({report.hypotheses.length})
            </button>
            <button
              onClick={() => setActiveTab("evidence")}
              className={`border-b-2 px-4 py-2.5 transition-colors ${
                activeTab === "evidence"
                  ? "border-zinc-900 text-zinc-950 dark:border-white dark:text-white"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              Evidence Records ({report.evidence.length})
            </button>
          </div>

          {/* Active Tab View */}
          <div>
            {activeTab === "summary" && <DiagnosticReportSummary report={report} />}
            {activeTab === "investigation" && (
              <AdaptiveInvestigationPanel
                stoppingReason={report.stopping_reason}
                investigationHistory={report.investigation_history}
                candidateProbes={report.candidate_probes}
                executedProbes={report.executed_probes}
              />
            )}
            {activeTab === "map" && <SystemMapViewer systemMap={report.system_map} />}
            {activeTab === "hypotheses" && (
              <HypothesisPanel
                hypotheses={report.hypotheses}
                verificationList={report.verification}
                onSelectEvidence={handleSelectEvidenceFromHypothesis}
              />
            )}
            {activeTab === "evidence" && (
              <EvidencePanel
                evidenceList={report.evidence}
                highlightedIds={highlightedEvidenceId ? [highlightedEvidenceId] : []}
              />
            )}
          </div>
        </div>
      )}

      {/* Empty State before any run */}
      {!report && !loading && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-zinc-200 p-12 text-center dark:border-zinc-800">
          <div className="rounded-full bg-zinc-100 p-3 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="mt-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            No Diagnostic Run Loaded
          </h3>
          <p className="mt-1 max-w-sm text-xs text-zinc-500 dark:text-zinc-400">
            {selectedRepo
              ? `Select analysis options and click "Initiate Diagnostic Run" to inspect ${selectedRepo.name}.`
              : "Register or select a target repository above to begin inspection."}
          </p>
        </div>
      )}
    </section>
  );
}
