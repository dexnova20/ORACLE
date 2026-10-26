"use client";

import React from "react";

const OPERATIONAL_STAGES = [
  {
    step: "01",
    title: "Target Validation",
    description: "Confirms target repository registration, capabilities, and execution policies.",
    status: "Operational",
  },
  {
    step: "02",
    title: "Safe Ingestion",
    description: "Bounded checkout and local containment verification with zero host execution.",
    status: "Operational",
  },
  {
    step: "03",
    title: "Static Inspection",
    description: "AST parsing, multi-ecosystem detection, and resource limit enforcement.",
    status: "Operational",
  },
  {
    step: "04",
    title: "System Mapping",
    description: "Constructs normalized component graph with line-level dependency provenance.",
    status: "Operational",
  },
  {
    step: "05",
    title: "Evidence Extraction",
    description: "Collects discrete empirical records with secret scrubbing and context limits.",
    status: "Operational",
  },
  {
    step: "06",
    title: "Hypothesis Synthesis",
    description: "Deterministic causal fault inference mapped to canonical taxonomy categories.",
    status: "Operational",
  },
  {
    step: "07",
    title: "Independent Verification",
    description: "Static AST validation and container sandbox preflight with host fallback guards.",
    status: "Operational",
  },
  {
    step: "08",
    title: "Forensic Reporting",
    description: "Produces reproducible diagnostic reports with recommendations and abstentions.",
    status: "Operational",
  },
];

export function DiagnosticWorkflowPreview() {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              ORACLE Diagnostic Pipeline Architecture
            </h2>
            <span className="rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
              End-to-End Operational
            </span>
          </div>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            A cohesive 8-stage pipeline connecting target registration, static analysis, evidence collection, and causal diagnosis.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {OPERATIONAL_STAGES.map((item) => (
          <div
            key={item.step}
            className="flex flex-col justify-between rounded-lg border border-zinc-200 bg-zinc-50/50 p-4 transition-colors hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950/50 dark:hover:border-zinc-700"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-zinc-400">
                  {item.step}
                </span>
                <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                  {item.status}
                </span>
              </div>
              <h3 className="mt-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {item.title}
              </h3>
              <p className="mt-1 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
                {item.description}
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 text-[10px] text-zinc-400 font-mono">
              Stage: {item.title.toLowerCase().replace(/ /g, "_")}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
