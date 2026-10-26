import React, { useState } from "react";
import { fetchHealth } from "@/lib/api";
import { HealthResponse, AsyncState } from "@/types/api";

export function HealthCheckAction() {
  const [healthState, setHealthState] = useState<AsyncState<HealthResponse>>({
    state: "idle",
  });
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const handleTestHealth = async () => {
    setHealthState({ state: "loading" });
    const startTime = performance.now();

    try {
      const data = await fetchHealth();
      const elapsed = Math.round(performance.now() - startTime);
      setLatencyMs(elapsed);
      setHealthState({
        state: "success",
        data,
        timestamp: new Date().toLocaleTimeString(),
      });
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - startTime);
      setLatencyMs(elapsed);
      const msg = err instanceof Error ? err.message : "Unknown error";
      setHealthState({
        state: "error",
        error: msg,
        timestamp: new Date().toLocaleTimeString(),
      });
    }
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            Health Check Probe
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Trigger an on-demand liveness probe to verify HTTP routing via{" "}
            <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-xs dark:bg-zinc-800">
              GET /api/v1/health
            </code>
          </p>
        </div>
        <button
          onClick={handleTestHealth}
          disabled={healthState.state === "loading"}
          className="inline-flex items-center rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {healthState.state === "loading" ? (
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
              Pinging API...
            </>
          ) : (
            <>Trigger Health Probe</>
          )}
        </button>
      </div>

      {healthState.state === "idle" && (
        <div className="mt-4 rounded-lg border border-dashed border-zinc-200 p-4 text-center text-xs text-zinc-400 dark:border-zinc-800">
          Click the button above to execute a real HTTP request against the backend endpoint.
        </div>
      )}

      {healthState.state === "loading" && (
        <div className="mt-4 rounded-lg bg-zinc-50 p-4 text-center text-xs text-zinc-500 dark:bg-zinc-950">
          Sending request to backend...
        </div>
      )}

      {healthState.state === "error" && (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/40 dark:bg-rose-950/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-rose-800 dark:text-rose-300">
              Health Probe Failed
            </span>
            {latencyMs !== null && (
              <span className="font-mono text-[11px] text-rose-600 dark:text-rose-400">
                {latencyMs}ms
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-rose-700 dark:text-rose-400">
            {healthState.error}
          </p>
        </div>
      )}

      {healthState.state === "success" && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 dark:border-emerald-950 dark:bg-emerald-950/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                HTTP 200 OK — Status: {healthState.data.status}
              </span>
            </div>
            {latencyMs !== null && (
              <span className="rounded bg-emerald-100 px-2 py-0.5 font-mono text-[11px] text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                Latency: {latencyMs}ms
              </span>
            )}
          </div>
          <pre className="mt-2 overflow-x-auto rounded bg-white p-3 font-mono text-xs text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-800">
            {JSON.stringify(healthState.data, null, 2)}
          </pre>
          <div className="mt-2 text-right text-[11px] text-zinc-400">
            Verified at {healthState.timestamp}
          </div>
        </div>
      )}
    </section>
  );
}
