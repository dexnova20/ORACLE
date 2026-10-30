"use client";

import React, { useState } from "react";
import Link from "next/link";

export function ScrollStoryNarrative() {
  // Section 2: Interactive secret scrubbing demo
  const [sampleRawTrace, setSampleRawTrace] = useState(
    'ConnectionError: Failed connecting to postgresql://admin:super_secret_jwt_9941a@db.internal:5432/orders'
  );

  // Section 4: Shannon entropy calculation simulation
  const [selectedProbeIndex, setSelectedProbeIndex] = useState<number>(0);

  const sampleProbes = [
    {
      id: "PROBE:AST_TOKEN_VALIDATION",
      type: "static_ast",
      target: "auth_service.ts:42",
      safety: "Safe (Read-Only AST)",
      cost: "Zero Execution Cost",
      entropyDrop: "-1.42 bits",
      confidenceAfter: "94% High Confidence",
    },
    {
      id: "PROBE:CONTAINER_IMPORT_CHECK",
      type: "docker_isolated",
      target: "secret_vault.Client",
      safety: "Restricted (Dropped Caps)",
      cost: "Moderate (Ephemeral Container)",
      entropyDrop: "-0.85 bits",
      confidenceAfter: "78% Medium Confidence",
    },
    {
      id: "PROBE:CONFIG_ENV_AUDIT",
      type: "manifest_audit",
      target: "pyproject.toml / package.json",
      safety: "Safe (Static Analysis)",
      cost: "Minimal",
      entropyDrop: "-0.32 bits",
      confidenceAfter: "61% Low Confidence",
    },
  ];

  return (
    <div id="system-story" className="space-y-24 py-20 bg-[#09090B] text-[#F5F3EF]">
      {/* Narrative Intro Divider */}
      <div className="mx-auto max-w-7xl px-6 text-center space-y-4">
        <span className="font-mono text-xs uppercase tracking-widest text-[#D4FF32] font-black">
          HOW ORACLE INVESTIGATES
        </span>
        <h2 className="text-4xl sm:text-5xl font-black tracking-tight text-[#F5F3EF] uppercase">
          Five stages of evidence-driven diagnosis
        </h2>
        <p className="text-sm text-[#85858D] max-w-xl mx-auto">
          Every technical failure leaves concrete evidence in AST syntax, dependency graphs, and runtime execution telemetry. ORACLE connects every thread.
        </p>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 1: Understand the System */}
      {/* ========================================================================= */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-10">
          <div className="lg:col-span-5 space-y-4">
            <div className="inline-flex items-center space-x-2 text-[10px] font-mono text-[#D4FF32] uppercase tracking-widest font-black">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32]" />
              <span>STAGE 01 • SYSTEM MAPPING</span>
            </div>
            <h3 className="text-2xl font-black tracking-tight text-[#F5F3EF] uppercase">
              Understand the entire system without executing untrusted code
            </h3>
            <p className="text-xs text-[#85858D] leading-relaxed">
              Before running any probes, ORACLE parses AST structures across Python, TypeScript/JavaScript, Java, and Go. It constructs an internal directed acyclic dependency graph, cataloging internal imports, external library versions, and unresolved symbols.
            </p>
            <div className="space-y-2 pt-2 text-xs font-mono">
              <div className="flex items-center space-x-2 text-[#F5F3EF]">
                <span className="text-[#D4FF32] font-black">✓</span>
                <span>Zero arbitrary host execution (pure read-only AST parsers)</span>
              </div>
              <div className="flex items-center space-x-2 text-[#F5F3EF]">
                <span className="text-[#D4FF32] font-black">✓</span>
                <span>Automatic detection of missing packages and unresolved imports</span>
              </div>
              <div className="flex items-center space-x-2 text-[#F5F3EF]">
                <span className="text-[#D4FF32] font-black">✓</span>
                <span>Exact file, line number, and AST statement attribution</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 bg-[#09090B] rounded border border-white/[0.08] p-5 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2 text-[11px] text-[#85858D]">
              <span className="font-bold uppercase tracking-wider">Polyglot Ecosystem Coverage</span>
              <span className="text-[#D4FF32] font-black uppercase">AST STATIC ANALYSIS</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
              <div className="p-3 rounded border border-white/[0.08] bg-[#151519]">
                <div className="font-black text-[#F5F3EF]">Python</div>
                <div className="text-[10px] text-[#85858D] mt-1">ast / pyproject</div>
              </div>
              <div className="p-3 rounded border border-[#D4FF32]/30 bg-[#151519]">
                <div className="font-black text-[#D4FF32]">TypeScript</div>
                <div className="text-[10px] text-[#85858D] mt-1">ts-morph / babel</div>
              </div>
              <div className="p-3 rounded border border-white/[0.08] bg-[#151519]">
                <div className="font-black text-[#F5F3EF]">Java</div>
                <div className="text-[10px] text-[#85858D] mt-1">javaparser / maven</div>
              </div>
              <div className="p-3 rounded border border-[#D4FF32]/30 bg-[#151519]">
                <div className="font-black text-[#D4FF32]">Go</div>
                <div className="text-[10px] text-[#85858D] mt-1">go/parser / go.mod</div>
              </div>
            </div>

            <div className="rounded bg-[#151519] p-3 text-[11px] border border-white/[0.08] space-y-1">
              <span className="text-[#85858D] block text-[10px] uppercase font-bold tracking-wider">Synthesized Graph Edge:</span>
              <div className="text-[#F5F3EF] truncate font-bold">
                {"comp:api_gateway.py"} <span className="text-[#D4FF32]">──[imports:auth]──&gt;</span> {"comp:auth_service.ts"}
              </div>
              <div className="text-[#85858D] text-[10px]">
                Coord: line 12 | import statement: `from services import auth` | Resolved: true
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 2: Investigate the Failure */}
      {/* ========================================================================= */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-10">
          <div className="lg:col-span-5 space-y-4">
            <div className="inline-flex items-center space-x-2 text-[10px] font-mono text-[#F20B91] uppercase tracking-widest font-black">
              <span className="h-1.5 w-1.5 rounded-full bg-[#F20B91]" />
              <span>STAGE 02 • EVIDENCE EXTRACTION &amp; PRIVACY</span>
            </div>
            <h3 className="text-2xl font-black tracking-tight text-[#F5F3EF] uppercase">
              Isolate discrete evidence while scrubbing sensitive credentials
            </h3>
            <p className="text-xs text-[#85858D] leading-relaxed">
              When runtime stack traces or log streams are supplied, ORACLE executes regex-based credential scrubbers to eliminate passwords, JWT bearer tokens, and API secret keys before persistence or model ranking.
            </p>
            <div className="space-y-2 pt-2 text-xs font-mono text-[#F5F3EF]">
              <div className="flex items-center space-x-2">
                <span className="text-[#F20B91] font-bold">🛡</span>
                <span>Automatic redacting of passwords, bearer tokens, AWS keys</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[#F20B91] font-bold">🛡</span>
                <span>Tagged reliability scores (Direct Observation vs Inferred Signal)</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 bg-[#09090B] rounded border border-white/[0.08] p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2 text-[11px] text-[#85858D]">
              <span className="font-bold uppercase tracking-wider">Live Credential Scrubber Simulation</span>
              <span className="text-[#D4FF32] font-black uppercase">SECURE HARNESS</span>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-[#85858D] uppercase font-bold">Input Raw Error / Traceback:</label>
              <textarea
                rows={2}
                value={sampleRawTrace}
                onChange={(e) => setSampleRawTrace(e.target.value)}
                className="w-full rounded border border-white/[0.1] bg-[#151519] p-2.5 text-[11px] text-[#F5F3EF] focus:outline-none focus:border-[#F20B91]"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-[#D4FF32] uppercase font-black flex items-center space-x-1">
                <span>Sanitized Diagnostic Evidence Record:</span>
              </label>
              <pre className="p-3 rounded border border-[#D4FF32]/40 bg-black/60 text-[#D4FF32] text-[11px] overflow-x-auto whitespace-pre-wrap">
                {sampleRawTrace
                  .replace(/super_secret_jwt_[a-zA-Z0-9]+/g, "[REDACTED_SECRET]")
                  .replace(/:admin:[^@]+@/g, ":admin:[REDACTED_PASSWORD]@")}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 3: Connect the Evidence */}
      {/* ========================================================================= */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-10">
          <div className="lg:col-span-5 space-y-4">
            <div className="inline-flex items-center space-x-2 text-[10px] font-mono text-[#D4FF32] uppercase tracking-widest font-black">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32]" />
              <span>STAGE 03 • CAUSAL HYPOTHESIS SYNTHESIS</span>
            </div>
            <h3 className="text-2xl font-black tracking-tight text-[#F5F3EF] uppercase">
              Connect observed evidence to competing causal explanations
            </h3>
            <p className="text-xs text-[#85858D] leading-relaxed">
              A single failure rarely has only one possible cause. ORACLE links each evidence item to competing hypotheses with explicit supporting or contradictory weights, preventing premature diagnostic lock-in.
            </p>
            <div className="space-y-2 pt-2 text-xs font-mono text-[#F5F3EF]">
              <div className="flex items-center space-x-2">
                <span className="text-[#D4FF32]">◈</span>
                <span>Bipartite graph linkage between evidence tokens &amp; hypotheses</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[#D4FF32]">◈</span>
                <span>Contradictory evidence explicitly penalizes invalid hypotheses</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 bg-[#09090B] rounded border border-white/[0.08] p-5 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2 text-[11px] text-[#85858D]">
              <span className="font-bold uppercase tracking-wider">Bipartite Evidence-to-Hypothesis Graph</span>
              <span className="text-[#D4FF32] font-black uppercase">WEIGHTED PROVENANCE</span>
            </div>

            <div className="space-y-2.5">
              {/* Hypothesis 1 */}
              <div className="p-3 rounded border border-[#F20B91]/50 bg-black/60 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-black text-[#F20B91]">HYPO_01: Syntax Error at auth_service.ts:42</span>
                  <span className="text-[10px] font-black text-[#09090B] bg-[#F20B91] px-2 py-0.5 rounded">
                    Rank 1 (94/100)
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                  <span className="text-[#D4FF32] bg-[#151519] px-2 py-0.5 rounded border border-[#D4FF32]/40 font-bold">
                    + EVID:AST_001 (Syntax error token)
                  </span>
                  <span className="text-[#D4FF32] bg-[#151519] px-2 py-0.5 rounded border border-[#D4FF32]/40 font-bold">
                    + EVID:DEP_003 (Upstream import caller)
                  </span>
                </div>
              </div>

              {/* Hypothesis 2 */}
              <div className="p-3 rounded border border-white/[0.08] bg-[#151519] space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-[#85858D]">HYPO_02: Database Connection Timeout</span>
                  <span className="text-[10px] font-mono text-[#85858D] bg-black/40 px-2 py-0.5 rounded">
                    Rank 2 (38/100)
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                  <span className="text-[#F20B91] bg-black px-2 py-0.5 rounded border border-[#F20B91]/40 font-bold">
                    - EVID:AST_001 (Compilation failure halts execution earlier)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 4: Determine What to Check Next */}
      {/* ========================================================================= */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-10">
          <div className="lg:col-span-5 space-y-4">
            <div className="inline-flex items-center space-x-2 text-[10px] font-mono text-[#F20B91] uppercase tracking-widest font-black">
              <span className="h-1.5 w-1.5 rounded-full bg-[#F20B91]" />
              <span>STAGE 04 • PROBE PLANNING (SHANNON ENTROPY)</span>
            </div>
            <h3 className="text-2xl font-black tracking-tight text-[#F5F3EF] uppercase">
              Determine what to check next using information gain
            </h3>
            <p className="text-xs text-[#85858D] leading-relaxed">
              Rather than executing random diagnostic tests, ORACLE ranks candidate probes by expected Shannon entropy reduction. It prioritizes probes that provide the highest discriminatory power with the lowest execution cost.
            </p>
            <div className="space-y-2 pt-2 text-xs font-mono text-[#F5F3EF]">
              <div className="flex items-center space-x-2">
                <span className="text-[#D4FF32] font-black">⚡</span>
                <span>Candidate probes classified by Safety Tier (Host Safe vs Docker Required)</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[#D4FF32] font-black">⚡</span>
                <span>Automatic stopping criteria prevent wasteful probe loops</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 bg-[#09090B] rounded border border-white/[0.08] p-5 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2 text-[11px] text-[#85858D]">
              <span className="font-bold uppercase tracking-wider">Candidate Probe Selection Matrix</span>
              <span className="text-[#D4FF32] font-black uppercase">ENTROPY GAIN</span>
            </div>

            {/* Interactive Probe Selector */}
            <div className="space-y-2">
              {sampleProbes.map((probe, idx) => (
                <button
                  key={probe.id}
                  onClick={() => setSelectedProbeIndex(idx)}
                  className={`w-full text-left p-3 rounded border transition-colors cursor-pointer ${
                    selectedProbeIndex === idx
                      ? "border-[#D4FF32] bg-[#151519] text-[#F5F3EF]"
                      : "border-white/[0.08] bg-black/40 text-[#85858D] hover:text-[#F5F3EF]"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-black">{probe.id}</span>
                    <span className="font-black text-[#D4FF32]">{probe.entropyDrop}</span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-[#85858D]">
                    <span>{probe.safety}</span>
                    <span>{probe.cost}</span>
                  </div>
                </button>
              ))}
            </div>

            {/* Probe Outcome Card */}
            <div className="p-3 rounded bg-[#151519] border border-white/[0.08] space-y-1">
              <span className="text-[10px] text-[#85858D] uppercase font-bold tracking-wider">Simulated Diagnostic Impact:</span>
              <div className="flex items-center justify-between text-xs text-[#F5F3EF]">
                <span>Resulting Certainty:</span>
                <span className="text-[#D4FF32] font-black">
                  {sampleProbes[selectedProbeIndex].confidenceAfter}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 5: Deliver the Diagnosis */}
      {/* ========================================================================= */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded border border-white/[0.08] bg-[#151519] p-6 sm:p-10">
          <div className="lg:col-span-5 space-y-4">
            <div className="inline-flex items-center space-x-2 text-[10px] font-mono text-[#D4FF32] uppercase tracking-widest font-black">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32]" />
              <span>STAGE 05 • EDITORIAL DELIVERABLE</span>
            </div>
            <h3 className="text-2xl font-black tracking-tight text-[#F5F3EF] uppercase">
              Deliver an editorial engineering report, not an AI hallucination
            </h3>
            <p className="text-xs text-[#85858D] leading-relaxed">
              ORACLE compiles a complete, actionable technical diagnosis report. Every assertion is backed by verifiable line coordinates, AST nodes, and confidence metrics—while openly communicating remaining uncertainties.
            </p>
            <div className="pt-3">
              <Link
                href="/diagnostics/new"
                className="inline-flex items-center space-x-2 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-5 py-3 text-xs tracking-wider transition-all shadow-[0_0_15px_rgba(242,11,145,0.3)]"
              >
                <span>LAUNCH DIAGNOSIS NOW</span>
                <span>→</span>
              </Link>
            </div>
          </div>

          <div className="lg:col-span-7 bg-[#09090B] rounded border border-white/[0.08] p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2 text-[11px] text-[#85858D]">
              <span className="font-bold uppercase tracking-wider">ORACLE Diagnostic Deliverable Preview</span>
              <span className="text-[#D4FF32] font-black uppercase">AUDIT READY</span>
            </div>

            <div className="space-y-2 text-[#F5F3EF] text-[11px]">
              <div className="p-3.5 rounded border border-white/[0.08] bg-[#151519] space-y-1">
                <span className="text-[10px] text-[#D4FF32] uppercase font-black block tracking-wider">
                  1. Executive Finding
                </span>
                <p className="text-[#F5F3EF]">
                  Compilation halted due to a syntax defect in `src/auth_service.ts` at line 42 (&ldquo;Unexpected token &apos;;&apos;&rdquo;). Upstream callers (`src/api_gateway.py`) fail to import authentication middlewares.
                </p>
              </div>

              <div className="p-3.5 rounded border border-white/[0.08] bg-[#151519] space-y-1">
                <span className="text-[10px] text-[#D4FF32] uppercase font-black block tracking-wider">
                  2. Prescribed Remediation
                </span>
                <p className="text-[#F5F3EF]">
                  Remove stray token at line 42 of `src/auth_service.ts`. Run TypeScript type-check before re-evaluating containerized integration tests.
                </p>
              </div>

              <div className="p-3.5 rounded border border-white/[0.08] bg-[#151519] space-y-1">
                <span className="text-[10px] text-[#F20B91] uppercase font-black block tracking-wider">
                  3. Remaining Uncertainty Notice
                </span>
                <p className="text-[#85858D]">
                  Dynamic container probes were skipped (Docker host isolation unavailable). Runtime latency under load has not been dynamically verified.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
