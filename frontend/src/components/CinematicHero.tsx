"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";

interface SystemNode {
  id: string;
  name: string;
  type: string;
  lang: string;
  x: number;
  y: number;
  status: "pending" | "analyzed" | "fault" | "unresolved";
  details?: string;
}

const NODES_DATA: SystemNode[] = [
  { id: "api_gateway", name: "api_gateway.py", type: "entrypoint", lang: "python", x: 44, y: 18, status: "analyzed" },
  { id: "fastapi", name: "fastapi", type: "external", lang: "pypi", x: 18, y: 18, status: "analyzed" },
  { id: "auth_service", name: "auth_service.ts", type: "service", lang: "typescript", x: 44, y: 52, status: "fault", details: "SyntaxError: Unexpected token ';' at line 42" },
  { id: "user_repo", name: "UserRepository.java", type: "repo", lang: "java", x: 74, y: 52, status: "analyzed" },
  { id: "unresolved_vault", name: "secret_vault", type: "unresolved", lang: "native", x: 18, y: 80, status: "unresolved", details: "Unresolved import symbol" },
  { id: "psycopg", name: "psycopg3", type: "external", lang: "pypi", x: 74, y: 80, status: "analyzed" },
];

const EDGES_DATA = [
  { from: "api_gateway", to: "fastapi", label: "import fastapi" },
  { from: "api_gateway", to: "auth_service", label: "from services import auth" },
  { from: "auth_service", to: "user_repo", label: "import { UserRepository }" },
  { from: "auth_service", to: "unresolved_vault", label: "import { SecretVault }" },
  { from: "user_repo", to: "psycopg", label: "import org.postgresql.Driver" },
];

const STAGE_DESCRIPTIONS = [
  "Empty system space: awaiting repository ingestion and structural mapping.",
  "Stage 1/9: Component discovery initiates across repository boundaries.",
  "Stage 2/9: Polyglot source nodes parsed (Python, TypeScript, Java, Go).",
  "Stage 3/9: Syntactic dependency graphs constructed via AST inspection.",
  "Stage 4/9: Data flow and call hierarchies traced across internal modules.",
  "Stage 5/9: Component health evaluation and lint verification executing.",
  "Stage 6/9: Critical defect localized in auth_service.ts (Syntax Error L42).",
  "Stage 7/9: Cascading dependency chain illuminated across caller paths.",
  "Stage 8/9: Discrete evidence record synthesised [EVID:AST_001].",
  "Stage 9/9: Live interactive environment settled. Inspect nodes below.",
];

export function CinematicHero() {
  const [stage, setStage] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [activeNodeId, setActiveNodeId] = useState<string | null>("auth_service");
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isPlaying) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setStage((prev) => {
        if (prev >= 9) {
          return 9;
        }
        return prev + 1;
      });
    }, 1800);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying]);

  const activeNode = NODES_DATA.find((n) => n.id === activeNodeId);

  return (
    <section className="relative overflow-hidden border-b border-white/[0.08] bg-[#09090B]">
      {/* Background technical coordinates & subtle atmosphere */}
      <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none" />
      <div className="cinematic-vignette absolute inset-0 pointer-events-none" />

      {/* Decorative hairline radar sweep in corner */}
      <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full border border-[#F20B91]/10 pointer-events-none flex items-center justify-center">
        <div className="w-64 h-64 rounded-full border border-[#D4FF32]/10 animate-pulse" />
      </div>

      <div className="mx-auto max-w-7xl px-6 py-16 sm:py-24 relative z-10 space-y-12">
        {/* Editorial Brand Narrative */}
        <div className="max-w-4xl space-y-6">
          <div className="inline-flex items-center space-x-2 rounded border border-[#F20B91]/40 bg-black/40 px-3 py-1 text-xs font-mono text-[#F5F3EF]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32] animate-pulse" />
            <span className="tracking-widest uppercase font-bold text-[10px] text-[#D4FF32]">
              ADAPTIVE TECHNICAL DIAGNOSIS PLATFORM
            </span>
          </div>

          <h1 className="text-5xl sm:text-7xl lg:text-8xl font-black tracking-tight text-[#F5F3EF] uppercase leading-[0.95]">
            FIND THE <span className="text-[#F20B91]">FAULT.</span><br />
            FOLLOW THE <span className="text-[#D4FF32]">EVIDENCE.</span>
          </h1>

          <p className="text-base sm:text-lg text-[#85858D] font-normal leading-relaxed max-w-2xl">
            ORACLE investigates technical failures across distributed components, isolates concrete AST and telemetry evidence, and calculates expected information gain to decide what to check next.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/diagnostics/new"
              className="flex items-center space-x-2 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-6 py-3.5 text-xs tracking-wider transition-all shadow-[0_0_20px_rgba(242,11,145,0.35)] active:scale-[0.98]"
            >
              <span>START DIAGNOSIS</span>
              <span className="text-sm">→</span>
            </Link>
            <a
              href="#system-story"
              className="rounded border border-white/[0.12] bg-[#151519] hover:bg-white/[0.08] text-[#F5F3EF] font-bold px-6 py-3.5 text-xs tracking-wider transition-colors"
            >
              EXPLORE THE SYSTEM
            </a>
          </div>
        </div>

        {/* 9-Stage Living System Visualization Showcase */}
        <div className="rounded border border-white/[0.1] bg-[#151519] p-2 sm:p-3 shadow-2xl relative">
          {/* Top Control & Stage Telemetry Bar */}
          <div className="flex flex-wrap items-center justify-between border-b border-white/[0.08] p-3 gap-3 bg-[#09090B] rounded-t">
            <div className="flex items-center space-x-3">
              <span className="font-mono text-xs font-black text-[#F5F3EF] flex items-center space-x-2">
                <span className="h-2 w-2 rounded-full bg-[#D4FF32] animate-pulse" />
                <span className="tracking-widest uppercase">INVESTIGATION CHRONOLOGY</span>
              </span>
              <span className="rounded bg-[#D4FF32]/10 border border-[#D4FF32]/30 px-2 py-0.5 font-mono text-[10px] text-[#D4FF32] font-bold">
                Interactive Demo
              </span>
            </div>

            {/* Stepper Controls */}
            <div className="flex items-center space-x-2 text-xs font-mono">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="px-2.5 py-1 rounded border border-white/[0.1] bg-[#151519] hover:bg-white/[0.08] text-[#F5F3EF] transition-colors text-[11px] font-bold"
              >
                {isPlaying ? "❚❚ Pause" : "▶ Resume"}
              </button>
              <button
                onClick={() => {
                  setStage(0);
                  setIsPlaying(true);
                }}
                className="px-2.5 py-1 rounded border border-white/[0.1] bg-[#151519] hover:bg-white/[0.08] text-[#85858D] hover:text-[#F5F3EF] transition-colors text-[11px]"
              >
                ↺ Replay
              </button>
              <button
                onClick={() => setStage(9)}
                className="px-2.5 py-1 rounded border border-[#F20B91]/40 bg-[#F20B91]/10 text-[#F20B91] hover:bg-[#F20B91]/20 transition-colors text-[11px] font-bold"
              >
                Skip to Interactive ⏭
              </button>
            </div>
          </div>

          {/* Narrative Stage Ticker */}
          <div className="px-4 py-2.5 bg-[#09090B] border-b border-white/[0.06] flex items-center justify-between text-xs font-mono">
            <div className="flex items-center space-x-2 text-[#F5F3EF] truncate">
              <span className="text-[#D4FF32] font-black">STAGE {stage}/9:</span>
              <span className="truncate text-[#85858D]">{STAGE_DESCRIPTIONS[stage]}</span>
            </div>
            {/* Scrubber dots */}
            <div className="hidden md:flex items-center space-x-1">
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setStage(s);
                    setIsPlaying(false);
                  }}
                  className={`h-2 rounded-full transition-all ${
                    s === stage
                      ? "w-5 bg-[#F20B91]"
                      : s < stage
                      ? "w-2 bg-[#D4FF32]"
                      : "w-2 bg-[#25252e]"
                  }`}
                  title={`Jump to step ${s}`}
                />
              ))}
            </div>
          </div>

          {/* Living Canvas Viewport */}
          <div className="relative min-h-[460px] w-full bg-[#09090B] bg-grid-pattern rounded-b overflow-hidden p-6 flex flex-col justify-between">
            {/* SVG Link Layer */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              <defs>
                <linearGradient id="hero-edge-fault" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#F20B91" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#F20B91" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="hero-edge-active" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#D4FF32" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#D4FF32" stopOpacity="0.4" />
                </linearGradient>
              </defs>

              {/* Draw Edges if stage >= 3 */}
              {stage >= 3 &&
                EDGES_DATA.map((edge, idx) => {
                  const srcNode = NODES_DATA.find((n) => n.id === edge.from);
                  const tgtNode = NODES_DATA.find((n) => n.id === edge.to);
                  if (!srcNode || !tgtNode) return null;

                  const isFaultChain =
                    (edge.from === "auth_service" || edge.to === "auth_service") && stage >= 6;
                  const isIlluminated =
                    (edge.from === "api_gateway" || edge.to === "user_repo") && stage >= 7;

                  return (
                    <g key={idx}>
                      <line
                        x1={`${srcNode.x}%`}
                        y1={`${srcNode.y}%`}
                        x2={`${tgtNode.x}%`}
                        y2={`${tgtNode.y}%`}
                        stroke={
                          isFaultChain
                            ? "url(#hero-edge-fault)"
                            : isIlluminated
                            ? "url(#hero-edge-active)"
                            : "#85858D"
                        }
                        strokeWidth={isFaultChain || isIlluminated ? "2" : "1"}
                        strokeDasharray={isFaultChain ? "3 3" : undefined}
                        strokeOpacity={isFaultChain || isIlluminated ? 1 : 0.25}
                      />
                      {/* Traveling Particle (Stage 4+) */}
                      {stage >= 4 && (
                        <circle
                          cx={`${(srcNode.x + tgtNode.x) / 2}%`}
                          cy={`${(srcNode.y + tgtNode.y) / 2}%`}
                          r={isFaultChain ? "3.5" : "2.5"}
                          fill={isFaultChain ? "#F20B91" : "#D4FF32"}
                          className={isFaultChain ? "animate-pulse" : undefined}
                        />
                      )}
                    </g>
                  );
                })}
            </svg>

            {/* Stage 0 Empty Placeholder */}
            {stage === 0 && (
              <div className="absolute inset-0 flex items-center justify-center flex-col space-y-2 text-center text-[#85858D] font-mono text-xs">
                <span className="text-[#D4FF32] font-black text-sm">System Canvas Initialized</span>
                <span>Connecting telemetry channels and AST parser pipelines...</span>
              </div>
            )}

            {/* Nodes Layer (Stage 1+) */}
            {stage >= 1 && (
              <div className="relative z-10 w-full h-full min-h-[380px]">
                {NODES_DATA.map((node) => {
                  const isFaultVisible = node.id === "auth_service" && stage >= 6;
                  const isChainHighlighted =
                    (node.id === "api_gateway" || node.id === "user_repo") && stage >= 7;
                  const isEvidenceTarget = node.id === "auth_service" && stage >= 8;
                  const isSelected = activeNodeId === node.id && stage === 9;

                  return (
                    <div
                      key={node.id}
                      onClick={() => {
                        if (stage === 9) setActiveNodeId(node.id);
                      }}
                      style={{
                        position: "absolute",
                        left: `${node.x}%`,
                        top: `${node.y}%`,
                        transform: "translate(-50%, -50%)",
                      }}
                      className={`cursor-pointer transition-all duration-500 select-none p-3.5 rounded border ${
                        isFaultVisible
                          ? "border-[#F20B91] bg-black/80 text-[#F5F3EF] shadow-[0_0_25px_rgba(242,11,145,0.4)] animate-fault-glitch"
                          : isChainHighlighted
                          ? "border-[#D4FF32] bg-black/80 text-[#F5F3EF] shadow-[0_0_15px_rgba(212,255,50,0.25)]"
                          : isSelected
                          ? "border-[#F20B91] bg-[#151519] text-[#F5F3EF] ring-2 ring-[#F20B91]/50"
                          : "border-white/[0.1] bg-[#151519] text-[#F5F3EF] hover:border-white/[0.25]"
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <span
                          className={`h-2 w-2 rounded-full ${
                            isFaultVisible
                              ? "bg-[#F20B91] animate-ping"
                              : node.status === "unresolved"
                              ? "bg-[#D4FF32]"
                              : "bg-[#D4FF32]"
                          }`}
                        />
                        <span className="font-mono text-xs font-bold tracking-tight text-[#F5F3EF]">
                          {node.name}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-[#85858D] font-mono mt-1 space-x-3">
                        <span>{node.type}</span>
                        <span className="text-[#D4FF32] font-black uppercase">{node.lang}</span>
                      </div>

                      {/* Evidence Pin Badge (Stage 8+) */}
                      {isEvidenceTarget && (
                        <div className="mt-2 text-[10px] font-mono bg-black text-[#F20B91] px-2 py-0.5 rounded border border-[#F20B91] flex items-center space-x-1 font-bold">
                          <span>🔍</span>
                          <span>EVID:AST_001 (Line 42)</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Stage 9 Inspector Drawer (Settled Interactive Mode) */}
            {stage === 9 && activeNode && (
              <div className="relative z-20 mt-4 rounded border border-white/[0.1] bg-[#151519] p-4 text-xs font-mono space-y-2">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-[#F5F3EF] font-black">{activeNode.name}</span>
                    <span className="text-[10px] text-[#85858D]">({activeNode.type})</span>
                  </div>
                  <span className="text-[10px] text-[#85858D] font-bold uppercase">
                    Status: {activeNode.status}
                  </span>
                </div>

                <div className="text-[11px] text-[#85858D]">
                  {activeNode.details ? (
                    <span className="text-[#F20B91] font-bold">{activeNode.details}</span>
                  ) : (
                    <span className="text-[#F5F3EF]">Analyzed and validated against AST module specifications. No faults discovered.</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
