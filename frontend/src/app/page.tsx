"use client";

import React, { useState } from "react";
import Link from "next/link";
import { InteractiveSystemMap } from "@/components/InteractiveSystemMap";

export default function LandingPage() {
  const [selectedDemoNode, setSelectedDemoNode] = useState<string | null>("comp:auth_service");

  return (
    <div className="min-h-screen bg-[#070a12] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation */}
      <header className="border-b border-slate-800/80 bg-[#090e1a]/80 backdrop-blur sticky top-0 z-50">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 font-bold text-white shadow-md shadow-cyan-500/20 text-sm">
              Ω
            </div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg tracking-tight text-white">ORACLE</span>
              <span className="rounded bg-cyan-950/80 border border-cyan-800/60 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-cyan-300">
                v0.1
              </span>
            </div>
          </Link>

          <nav className="flex items-center space-x-6 text-xs font-medium">
            <Link href="#capabilities" className="text-slate-400 hover:text-slate-200 transition-colors">
              Capabilities
            </Link>
            <Link href="#workflow" className="text-slate-400 hover:text-slate-200 transition-colors">
              Workflow
            </Link>
            <Link href="/dashboard" className="text-slate-300 hover:text-cyan-300 transition-colors">
              Dashboard
            </Link>
            <Link
              href="/diagnostics/new"
              className="rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-3.5 py-2 transition-all shadow-sm shadow-cyan-500/20"
            >
              Start Diagnosis
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-16 sm:py-24 border-b border-slate-800/60">
        {/* Subtle background glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-cyan-500/5 blur-[120px] rounded-full pointer-events-none" />

        <div className="mx-auto max-w-7xl px-6 relative z-10 space-y-12">
          {/* Hero Header */}
          <div className="max-w-3xl space-y-5">
            <div className="inline-flex items-center space-x-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3 py-1 text-xs font-mono text-cyan-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>Adaptive Technical Diagnosis Platform</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.1]">
              Find the fault. <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-violet-400">
                Follow the evidence.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl font-normal">
              ORACLE investigates technical failures, connects evidence across system components, and helps you identify what to check next.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                href="/diagnostics/new"
                className="flex items-center space-x-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-5 py-3 text-xs transition-all shadow-md shadow-cyan-500/25 active:scale-[0.98]"
              >
                <span>Start Diagnosis</span>
                <span>→</span>
              </Link>
              <Link
                href="#capabilities"
                className="rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-700/60 text-slate-200 font-semibold px-5 py-3 text-xs transition-colors"
              >
                Explore How It Works
              </Link>
            </div>
          </div>

          {/* Visual Centerpiece: Interactive System Dependency Map */}
          <div className="rounded-2xl border border-slate-800 bg-[#0a0f1d] p-2 shadow-2xl shadow-black/80">
            <div className="border border-slate-800/80 rounded-xl overflow-hidden min-h-[460px]">
              <InteractiveSystemMap
                highlightedComponentId={selectedDemoNode}
                onSelectComponent={setSelectedDemoNode}
                isDemo={true}
              />
            </div>
          </div>
        </div>
      </section>

      {/* 3 Core Capabilities */}
      <section id="capabilities" className="py-20 border-b border-slate-800/60 bg-[#090d18]">
        <div className="mx-auto max-w-7xl px-6 space-y-12">
          <div className="max-w-2xl space-y-2">
            <span className="text-xs uppercase font-bold tracking-wider text-cyan-400 font-mono">
              Core Diagnostic Capabilities
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              An engineering investigation room for complex failures
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Capability 1 */}
            <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-3 hover:border-slate-700 transition-colors">
              <div className="h-8 w-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center font-bold text-sm">
                1
              </div>
              <h3 className="text-base font-bold text-slate-100">
                Understand the System
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Map components, internal dependencies, external packages, and unresolved references across Python, TypeScript/JS, Java, and Go without executing uncontained code on the host.
              </p>
            </div>

            {/* Capability 2 */}
            <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-3 hover:border-slate-700 transition-colors">
              <div className="h-8 w-8 rounded-lg bg-violet-500/10 border border-violet-500/30 text-violet-400 flex items-center justify-center font-bold text-sm">
                2
              </div>
              <h3 className="text-base font-bold text-slate-100">
                Investigate the Failure
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Combine AST static inspection, runtime telemetry stack traces, and manifest audits to gather discrete evidence records while automatically scrubbing sensitive credentials.
              </p>
            </div>

            {/* Capability 3 */}
            <div className="rounded-xl border border-slate-800/80 bg-[#0d1424] p-6 space-y-3 hover:border-slate-700 transition-colors">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-bold text-sm">
                3
              </div>
              <h3 className="text-base font-bold text-slate-100">
                Narrow Down the Cause
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Compare competing hypotheses using information gain (Shannon entropy), expose remaining uncertainty honestly, and recommend the next discriminatory check.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Concise Workflow Section */}
      <section id="workflow" className="py-20 border-b border-slate-800/60 bg-[#070a12]">
        <div className="mx-auto max-w-7xl px-6 space-y-10">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs uppercase font-bold tracking-wider text-cyan-400 font-mono">
              Investigation Pipeline
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              From repository ingestion to verified diagnosis
            </h2>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-mono">
            {["Ingest", "Map", "Investigate", "Verify", "Report"].map((step, idx) => (
              <React.Fragment key={step}>
                <div className="flex items-center space-x-2 rounded-lg border border-slate-800 bg-[#0d1424] px-4 py-2.5 text-slate-200">
                  <span className="text-cyan-400 font-bold">{idx + 1}.</span>
                  <span className="font-semibold text-slate-100">{step}</span>
                </div>
                {idx < 4 && <span className="text-slate-600 font-bold">→</span>}
              </React.Fragment>
            ))}
          </div>

          <div className="text-center pt-4">
            <Link
              href="/diagnostics/new"
              className="inline-flex items-center space-x-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-6 py-3 text-xs transition-all shadow-md shadow-cyan-500/20 active:scale-[0.98]"
            >
              <span>Launch Diagnostic Investigation</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Minimal Footer */}
      <footer className="py-8 bg-[#050810] border-t border-slate-800/60 text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-2 font-mono">
            <span className="text-cyan-400 font-bold">Ω ORACLE</span>
            <span>v0.1.0-alpha • Adaptive Technical Diagnosis Platform</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/dashboard" className="hover:text-slate-300 transition-colors">
              Dashboard
            </Link>
            <Link href="/workspace" className="hover:text-slate-300 transition-colors">
              Workspace
            </Link>
            <Link href="/history" className="hover:text-slate-300 transition-colors">
              Run History
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
