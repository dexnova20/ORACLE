import React from "react";
import { SystemStatusResponse, AsyncState } from "@/types/api";

interface StatusCardProps {
  statusState: AsyncState<SystemStatusResponse>;
  onRefresh: () => void;
}

export function StatusCard({ statusState, onRefresh }: StatusCardProps) {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            System &amp; Database Diagnostics
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Live infrastructure probe reporting via{" "}
            <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-xs dark:bg-zinc-800">
              GET /api/v1/status
            </code>
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={statusState.state === "loading"}
          className="inline-flex items-center rounded-lg bg-zinc-900 px-3.5 py-2 text-xs font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          {statusState.state === "loading" ? (
            <>
              <svg
                className="mr-2 h-3.5 w-3.5 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Checking...
            </>
          ) : (
            <>Refresh Status</>
          )}
        </button>
      </div>

      {statusState.state === "loading" && (
        <div className="flex h-36 items-center justify-center rounded-lg border border-dashed border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center space-x-2 text-sm text-zinc-500">
            <span className="h-2 w-2 animate-ping rounded-full bg-zinc-400" />
            <span>Querying backend status probe...</span>
          </div>
        </div>
      )}

      {statusState.state === "error" && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/50 dark:bg-rose-950/20">
          <div className="flex items-start space-x-3">
            <span className="text-rose-600 dark:text-rose-400">⚠️</span>
            <div>
              <h3 className="text-sm font-semibold text-rose-800 dark:text-rose-300">
                Backend Service Unavailable
              </h3>
              <p className="mt-1 text-xs text-rose-700 dark:text-rose-400">
                {statusState.error}
              </p>
              <div className="mt-3 rounded bg-white/80 p-2 font-mono text-[11px] text-zinc-700 dark:bg-zinc-900/80 dark:text-zinc-300">
                Ensure FastAPI server is running:{" "}
                <span className="font-bold text-zinc-900 dark:text-white">
                  cd backend; ..\.venv\Scripts\python.exe -m uvicorn oracle.main:app --port 8000
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {statusState.state === "success" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Core Application Status */}
            <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-800 dark:bg-zinc-950/50">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  FastAPI Application
                </span>
                <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                  {statusState.data.app.status}
                </span>
              </div>
              <dl className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <dt className="text-zinc-500">Application Name:</dt>
                  <dd className="font-semibold text-zinc-900 dark:text-zinc-100">
                    {statusState.data.app.app_name}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-zinc-500">Version:</dt>
                  <dd className="font-mono text-zinc-900 dark:text-zinc-100">
                    {statusState.data.app.version}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-zinc-500">Environment:</dt>
                  <dd className="capitalize text-zinc-900 dark:text-zinc-100">
                    {statusState.data.app.environment}
                  </dd>
                </div>
              </dl>
            </div>

            {/* PostgreSQL Status */}
            <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-800 dark:bg-zinc-950/50">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  PostgreSQL Persistence
                </span>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    statusState.data.database.connected
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                      : "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                  }`}
                >
                  {statusState.data.database.connected ? "Operational" : "Not Reachable"}
                </span>
              </div>
              <dl className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <dt className="text-zinc-500">Driver:</dt>
                  <dd className="font-mono text-zinc-900 dark:text-zinc-100">
                    {statusState.data.database.driver}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-zinc-500">Persistence Mode:</dt>
                  <dd className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                    {statusState.data.persistence_mode || (statusState.data.database.connected ? "durable_postgresql" : "in_memory_transient")}
                  </dd>
                </div>
                <div className="pt-1">
                  <dt className="text-zinc-500">Connection Message:</dt>
                  <dd className="mt-1 break-words rounded bg-white p-2 font-mono text-[11px] text-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800">
                    {statusState.data.database.message}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Execution Isolation & Polyglot Engine */}
            <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-800 dark:bg-zinc-950/50 sm:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    Dynamic Isolation:
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      statusState.data.docker_isolation_available
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                        : "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                    }`}
                  >
                    {statusState.data.docker_isolation_available ? "Docker Operational" : "Unavailable (Host Fallback Blocked)"}
                  </span>
                </div>
                <div className="flex items-center space-x-1.5 text-xs text-zinc-500">
                  <span>Languages:</span>
                  {(statusState.data.supported_languages || ["python", "typescript", "javascript", "java"]).map((lang) => (
                    <span
                      key={lang}
                      className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-zinc-400">
            <span>Last checked: {statusState.timestamp}</span>
            <span>Policy: Strictly PostgreSQL (No SQLite fallbacks)</span>
          </div>
        </div>
      )}
    </section>
  );
}
