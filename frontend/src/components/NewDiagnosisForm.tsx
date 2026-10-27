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

  // State
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
          throw new Error("Repository display name and URL path are required.");
        }
        setProgressStage("Registering repository metadata & validating URI scheme...");
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

      setProgressStage("Executing polyglot static inspection & hypothesis synthesis...");
      const report = await startDiagnosticRun(targetId, {
        allow_dynamic: allowDynamic,
        symptom_description: symptomText.trim() || undefined,
        runtime_traceback: tracebackText.trim() || undefined,
      });

      setProgressStage("Diagnosis completed successfully.");
      if (onDiagnosisComplete) {
        onDiagnosisComplete(report);
      }
      router.push("/workspace");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute diagnostic run.";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
      setProgressStage(null);
    }
  };

  return (
    <div className="max-w-3xl mx-auto rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100 tracking-tight">
          Start Diagnostic Investigation
        </h1>
        <p className="text-xs text-slate-400 mt-1 leading-relaxed">
          ORACLE inspects source code, dependencies, and runtime symptoms to identify root causes and plan discriminatory probes without executing uncontained code on the host.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Mode Selector */}
        <div className="flex rounded-lg border border-slate-800 bg-[#080d19] p-1 text-xs">
          <button
            type="button"
            onClick={() => setMode("existing")}
            disabled={existingRepositories.length === 0}
            className={`flex-1 py-2 rounded-md font-semibold transition-colors ${
              mode === "existing"
                ? "bg-cyan-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-slate-200 disabled:opacity-40"
            }`}
          >
            Registered Target ({existingRepositories.length})
          </button>
          <button
            type="button"
            onClick={() => setMode("new")}
            className={`flex-1 py-2 rounded-md font-semibold transition-colors ${
              mode === "new"
                ? "bg-cyan-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            + Register New Target
          </button>
        </div>

        {/* Existing Repo Select */}
        {mode === "existing" && (
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              Select Target Repository:
            </label>
            <select
              value={selectedRepoId}
              onChange={(e) => setSelectedRepoId(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-[#080d19] px-3.5 py-2.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
            >
              {existingRepositories.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name} ({repo.url})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* New Repo Form */}
        {mode === "new" && (
          <div className="space-y-4 rounded-lg border border-slate-800/80 bg-[#0a0f1d] p-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Target Display Name:
              </label>
              <input
                type="text"
                required
                placeholder="e.g. auth-service-production"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-[#080d19] px-3.5 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">
                  Repository Location URI:
                </label>
                <span className="text-[10px] text-slate-500 font-mono">
                  file:// or https:// scheme required
                </span>
              </div>
              <input
                type="text"
                required
                placeholder="file:///path/to/local/repo or https://github.com/org/repo.git"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-[#080d19] px-3.5 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Source VCS Layout:
              </label>
              <div className="flex gap-4 text-xs text-slate-300">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="sourceType"
                    value="local_directory"
                    checked={sourceType === "local_directory"}
                    onChange={() => setSourceType("local_directory")}
                    className="text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>Local Directory (`file://`)</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="sourceType"
                    value="git"
                    checked={sourceType === "git"}
                    onChange={() => setSourceType("git")}
                    className="text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>Remote Git (`https://`)</span>
                </label>
              </div>
            </div>

            {/* Input Format Help Box */}
            <div className="rounded-lg border border-slate-800 bg-[#080d19] p-3 text-[11px] text-slate-400 space-y-1">
              <span className="font-semibold text-slate-300 block">Supported Ecosystems &amp; Manifests:</span>
              <p>• Python (`pyproject.toml`, `requirements.txt`)</p>
              <p>• TypeScript &amp; JavaScript (`package.json`, `tsconfig.json`)</p>
              <p>• Java (`pom.xml`, `build.gradle`)</p>
              <p>• Go (`go.mod`)</p>
            </div>
          </div>
        )}

        {/* Runtime Telemetry (Collapsible) */}
        <div className="rounded-lg border border-slate-800/80 bg-[#0a0f1d] overflow-hidden">
          <button
            type="button"
            onClick={() => setShowTelemetry(!showTelemetry)}
            className="w-full flex items-center justify-between p-4 text-xs font-semibold text-slate-200 hover:bg-slate-800/30 transition-colors text-left"
          >
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Optional: Runtime Telemetry &amp; Stack Trace</span>
            </div>
            <span className="text-[11px] text-cyan-400 font-mono">
              {showTelemetry ? "Collapse ▲" : "Add Error Logs ▼"}
            </span>
          </button>

          {showTelemetry && (
            <div className="p-4 pt-0 space-y-4 border-t border-slate-800/60 mt-1">
              <div className="rounded border border-emerald-500/20 bg-emerald-950/20 px-3 py-1.5 text-[11px] text-emerald-300 flex items-center space-x-1.5">
                <span>🛡</span>
                <span>Automated Secret Redaction Active: Passwords, tokens, and keys are automatically scrubbed.</span>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Observed Symptom Description:
                </label>
                <input
                  type="text"
                  placeholder="e.g. Database connection timed out after 5000ms during login query"
                  value={symptomText}
                  onChange={(e) => setSymptomText(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-[#080d19] px-3.5 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Runtime Stack Trace / Traceback Excerpt:
                </label>
                <textarea
                  rows={4}
                  placeholder="Paste Python, Node, Java, or Go panic traceback here..."
                  value={tracebackText}
                  onChange={(e) => setTracebackText(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-[#080d19] px-3.5 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none font-mono"
                />
              </div>
            </div>
          )}
        </div>

        {/* Dynamic Execution Policy Toggle */}
        <div className="rounded-lg border border-slate-800 bg-[#0a0f1d] p-4 text-xs space-y-2">
          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={allowDynamic}
              onChange={(e) => setAllowDynamic(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
            />
            <div className="space-y-0.5">
              <span className="font-semibold text-slate-200 block">
                Allow Containerized Dynamic Verification (if Docker available)
              </span>
              <p className="text-[11px] text-slate-400">
                Arbitrary host execution is prohibited. When enabled, probes run inside isolated Docker containers with dropped Linux capabilities. If Docker is absent, dynamic probes are safely skipped.
              </p>
            </div>
          </label>
        </div>

        {/* Error Banner */}
        {errorMessage && (
          <div className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-3.5 text-xs text-rose-200 flex items-start space-x-2">
            <span className="text-rose-400 font-bold shrink-0">✕</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Action Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center space-x-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-5 py-3 text-xs transition-all shadow-md shadow-cyan-500/20 active:scale-[0.99] disabled:opacity-50 cursor-pointer"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4 text-slate-950" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>{progressStage || "Investigating Target..."}</span>
            </>
          ) : (
            <span>Run Diagnostic Investigation →</span>
          )}
        </button>
      </form>
    </div>
  );
}
