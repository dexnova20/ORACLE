"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { registerRepository, startDiagnosticRun } from "@/lib/api";
import { DiagnosticReport, Repository } from "@/types/api";

interface NewDiagnosisFormProps {
  existingRepositories: Repository[];
  onDiagnosisComplete?: (report: DiagnosticReport) => void;
}

export function NewDiagnosisForm({
  existingRepositories,
  onDiagnosisComplete,
}: NewDiagnosisFormProps) {
  const router = useRouter();

  // Mode: "existing" or "new"
  const [mode, setMode] = useState<"existing" | "new">(
    existingRepositories.length > 0 ? "existing" : "new"
  );

  // Existing selection
  const [selectedRepoId, setSelectedRepoId] = useState<string>(
    existingRepositories.length > 0 ? existingRepositories[0].id : ""
  );

  // New registration fields
  const [repoName, setRepoName] = useState<string>("");
  const [repoUrl, setRepoUrl] = useState<string>("");
  const [sourceType, setSourceType] = useState<"local_directory" | "git">("local_directory");

  // Telemetry & options
  const [symptomText, setSymptomText] = useState<string>("");
  const [tracebackText, setTracebackText] = useState<string>("");
  const [allowDynamic, setAllowDynamic] = useState<boolean>(false);
  const [showTelemetry, setShowTelemetry] = useState<boolean>(false);

  // State & Multi-stage submission feedback
  const [loading, setLoading] = useState<boolean>(false);
  const [progressStage, setProgressStage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setLoading(true);
    setProgressStage("Initiating diagnostic target ingestion...");

    try {
      let targetId = selectedRepoId;

      if (mode === "new") {
        if (!repoName.trim() || !repoUrl.trim()) {
          throw new Error("Repository display name and URI location are required.");
        }
        setProgressStage("Validating URI scheme and registering target repository...");
        const newRepo = await registerRepository({
          name: repoName.trim(),
          url: repoUrl.trim(),
          source_type: sourceType,
        });
        targetId = newRepo.id;
      }

      if (!targetId) {
        throw new Error("Please select or register a repository target.");
      }

      setProgressStage("Executing polyglot static inspection & AST dependency mapping...");
      const report = await startDiagnosticRun(targetId, {
        allow_dynamic: allowDynamic,
        symptom_description: symptomText.trim() || undefined,
        runtime_traceback: tracebackText.trim() || undefined,
      });

      setProgressStage("Investigation complete. Opening diagnostic workspace...");
      if (onDiagnosisComplete) {
        onDiagnosisComplete(report);
      }
      router.push("/workspace");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute diagnostic run.";
      setErrorMessage(msg);
      setLoading(false);
      setProgressStage(null);
    }
  };

  return (
    <div className="max-w-3xl mx-auto rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-8 space-y-6">
      {/* Terminal Title & Invariants */}
      <div className="border-b border-white/[0.08] pb-4 space-y-1.5">
        <div className="flex items-center space-x-2">
          <span className="h-2 w-2 rounded-full bg-[#D4FF32]" />
          <h1 className="text-xl font-black text-[#F5F3EF] tracking-tight font-mono uppercase">
            Diagnostic Investigation Launcher
          </h1>
        </div>
        <p className="text-xs text-[#85858D] font-mono leading-relaxed">
          Configure a diagnostic investigation against a local directory or remote Git repository. Ingestion invokes pure read-only AST parsers and secret-scrubbed telemetry analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 text-xs font-mono">
        {/* Mode Selector Tabs */}
        <div className="flex items-center rounded border border-white/[0.08] bg-[#09090B] p-1 text-xs">
          <button
            type="button"
            onClick={() => setMode("existing")}
            disabled={existingRepositories.length === 0}
            className={`flex-1 py-2 rounded text-center transition-colors cursor-pointer ${
              mode === "existing"
                ? "bg-[#D4FF32] text-[#09090B] font-black"
                : "text-[#85858D] hover:text-[#F5F3EF] disabled:opacity-30 disabled:cursor-not-allowed"
            }`}
          >
            Select Existing Target ({existingRepositories.length})
          </button>
          <button
            type="button"
            onClick={() => setMode("new")}
            className={`flex-1 py-2 rounded text-center transition-colors cursor-pointer ${
              mode === "new"
                ? "bg-[#D4FF32] text-[#09090B] font-black"
                : "text-[#85858D] hover:text-[#F5F3EF]"
            }`}
          >
            + Register New Codebase Target
          </button>
        </div>

        {/* Existing Target Dropdown */}
        {mode === "existing" && (
          <div className="space-y-2">
            <label className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider block">
              Registered Target Repository
            </label>
            <select
              value={selectedRepoId}
              onChange={(e) => setSelectedRepoId(e.target.value)}
              className="w-full rounded border border-white/[0.08] bg-[#09090B] px-3.5 py-2.5 text-[#F5F3EF] focus:border-[#F20B91] focus:outline-none"
            >
              {existingRepositories.map((repo) => (
                <option key={repo.id} value={repo.id} className="bg-[#151519] text-[#F5F3EF]">
                  {repo.name} — {repo.url} ({repo.source_type})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* New Target Registration Fields */}
        {mode === "new" && (
          <div className="space-y-4 rounded border border-white/[0.08] bg-[#09090B] p-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider block">
                Target Display Name
              </label>
              <input
                type="text"
                placeholder="e.g. Orders Microservice"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                className="w-full rounded border border-white/[0.08] bg-[#151519] px-3.5 py-2 text-[#F5F3EF] placeholder-[#85858D] focus:border-[#F20B91] focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider block">
                  Target URI Scheme
                </label>
                <span className="text-[10px] text-[#85858D]">
                  Use <code className="text-[#D4FF32]">file:///...</code> for local directories
                </span>
              </div>
              <input
                type="text"
                placeholder="file:///c:/path/to/project or https://github.com/org/repo.git"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="w-full rounded border border-white/[0.08] bg-[#151519] px-3.5 py-2 text-[#F5F3EF] placeholder-[#85858D] focus:border-[#F20B91] focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider block">
                Source Type
              </label>
              <div className="flex items-center space-x-4 text-xs text-[#85858D]">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="sourceType"
                    value="local_directory"
                    checked={sourceType === "local_directory"}
                    onChange={() => setSourceType("local_directory")}
                    className="accent-[#F20B91]"
                  />
                  <span className="text-[#F5F3EF]">Local Directory (Absolute Path)</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="sourceType"
                    value="git"
                    checked={sourceType === "git"}
                    onChange={() => setSourceType("git")}
                    className="accent-[#F20B91]"
                  />
                  <span className="text-[#F5F3EF]">Git Repository</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Runtime Telemetry Input (Collapsible) */}
        <div className="rounded border border-white/[0.08] bg-[#09090B] p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="font-bold text-[#F5F3EF] block">
                Runtime Error Telemetry &amp; Stack Traces
              </span>
              <span className="text-[11px] text-[#85858D]">
                Provide runtime error messages to correlate stack frames with static AST nodes.
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowTelemetry(!showTelemetry)}
              className="text-xs text-[#D4FF32] hover:underline cursor-pointer font-bold"
            >
              {showTelemetry ? "Hide Telemetry" : "+ Attach Traceback"}
            </button>
          </div>

          {showTelemetry && (
            <div className="space-y-3 pt-2">
              <div className="space-y-1">
                <label className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider block">
                  Observed Symptom Description
                </label>
                <input
                  type="text"
                  placeholder="e.g. Internal Server Error 500 on POST /auth/login"
                  value={symptomText}
                  onChange={(e) => setSymptomText(e.target.value)}
                  className="w-full rounded border border-white/[0.08] bg-[#151519] px-3.5 py-2 text-[#F5F3EF] placeholder-[#85858D] focus:border-[#F20B91] focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider block">
                    Raw Traceback / Log Excerpt
                  </label>
                  <span className="text-[10px] text-[#D4FF32] flex items-center space-x-1 font-bold">
                    <span>🛡 Secret Redaction Active</span>
                  </span>
                </div>
                <textarea
                  rows={4}
                  placeholder="Paste Python traceback, Node.js TypeError, or Java Exception..."
                  value={tracebackText}
                  onChange={(e) => setTracebackText(e.target.value)}
                  className="w-full rounded border border-white/[0.08] bg-[#151519] p-3 text-[11px] text-[#F5F3EF] placeholder-[#85858D] focus:border-[#F20B91] focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Security / Dynamic Execution Gating Toggle */}
        <div className="rounded border border-white/[0.08] bg-[#09090B] p-4 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <span className="font-bold text-[#F5F3EF] block">
              Containerized Dynamic Probe Execution
            </span>
            <p className="text-[11px] text-[#85858D] leading-relaxed">
              When enabled, probes are dispatched into isolated, ephemeral Docker containers with dropped capabilities. If Docker daemon is unavailable, ORACLE safely falls back to pure read-only AST inspection.
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
            <input
              type="checkbox"
              checked={allowDynamic}
              onChange={(e) => setAllowDynamic(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-[#151519] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#F20B91]"></div>
          </label>
        </div>

        {/* Error Feedback */}
        {errorMessage && (
          <div className="rounded border border-[#F20B91]/40 bg-black/60 p-3 text-xs text-[#F20B91] flex items-center space-x-2 font-bold">
            <span>⚠ Error:</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Multi-Stage Submission Progress Ticker */}
        {loading && progressStage && (
          <div className="rounded border border-[#D4FF32]/40 bg-black/60 p-3 space-y-1.5 font-mono text-xs">
            <div className="flex items-center space-x-2 text-[#D4FF32]">
              <span className="h-2 w-2 rounded-full bg-[#D4FF32] animate-pulse" />
              <span className="font-black uppercase tracking-wider text-[10px]">DIAGNOSTIC PIPELINE DISPATCHED</span>
            </div>
            <p className="text-[#F5F3EF] text-[11px]">{progressStage}</p>
          </div>
        )}

        {/* Submit Action */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black py-3 text-xs tracking-wider transition-all shadow-[0_0_20px_rgba(242,11,145,0.35)] active:scale-[0.99] disabled:opacity-50 cursor-pointer"
          >
            <span>{loading ? "ANALYZING TARGET..." : "DISPATCH INVESTIGATION ENGINE"}</span>
            <span className="text-sm">→</span>
          </button>
        </div>
      </form>
    </div>
  );
}
