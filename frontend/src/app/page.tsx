"use client";

import React from "react";
import Link from "next/link";
import { CinematicHero } from "@/components/CinematicHero";
import { ScrollStoryNarrative } from "@/components/ScrollStoryNarrative";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#09090B] text-[#F5F3EF] flex flex-col font-sans selection:bg-[#F20B91] selection:text-[#09090B]">
      {/* Top Editorial Navigation */}
      <header className="border-b border-white/[0.08] bg-[#151519]/90 backdrop-blur sticky top-0 z-50">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-black/40 border border-[#F20B91]/60 text-[#F20B91] font-mono font-black text-sm tracking-tighter group-hover:border-[#D4FF32] group-hover:text-[#D4FF32] transition-colors">
              Ω
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="font-black text-base tracking-tight text-[#F5F3EF] group-hover:text-[#F20B91] transition-colors">
                ORACLE
              </span>
              <span className="font-mono text-[10px] text-[#85858D] font-bold">
                v0.1
              </span>
            </div>
          </Link>

          <nav className="flex items-center space-x-6 text-xs font-mono">
            <a href="#system-story" className="text-[#85858D] hover:text-[#F5F3EF] transition-colors hidden sm:inline font-bold">
              Investigation Story
            </a>
            <Link href="/dashboard" className="text-[#85858D] hover:text-[#D4FF32] transition-colors font-bold">
              Dashboard
            </Link>
            <Link href="/workspace" className="text-[#85858D] hover:text-[#D4FF32] transition-colors hidden sm:inline font-bold">
              Workspace
            </Link>
            <Link
              href="/diagnostics/new"
              className="rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-4 py-2 transition-all shadow-[0_0_15px_rgba(242,11,145,0.3)] text-xs tracking-wider"
            >
              START DIAGNOSIS
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Narrative Body */}
      <main className="flex-1">
        {/* Full-viewport Cinematic Hero with 9-Stage Story */}
        <CinematicHero />

        {/* 5-Stage Editorial Scroll-Based Investigation Story */}
        <ScrollStoryNarrative />
      </main>

      {/* Minimal Engineering Footer */}
      <footer className="py-10 bg-[#09090B] border-t border-white/[0.08] text-xs font-mono text-[#85858D]">
        <div className="mx-auto max-w-7xl px-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="text-[#F20B91] font-black">Ω ORACLE</span>
            <span>v0.1.0 • Adaptive Technical Diagnosis Platform</span>
          </div>
          <div className="flex items-center space-x-5 text-[11px] font-bold">
            <Link href="/dashboard" className="hover:text-[#F5F3EF] transition-colors">
              Dashboard
            </Link>
            <Link href="/workspace" className="hover:text-[#F5F3EF] transition-colors">
              Investigation Room
            </Link>
            <Link href="/history" className="hover:text-[#F5F3EF] transition-colors">
              Run History
            </Link>
            <Link href="/diagnostics/new" className="text-[#D4FF32] hover:text-[#F5F3EF] transition-colors">
              Launch Diagnosis →
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
