"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { fetchStatus } from "@/lib/api";
import { SystemStatusResponse } from "@/types/api";

interface AppShellProps {
  children: React.ReactNode;
  activeTargetName?: string;
}

export function AppShell({ children, activeTargetName }: AppShellProps) {
  const pathname = usePathname();
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    fetchStatus()
      .then((data) => {
        if (isMounted) {
          setStatus(data);
          setIsOnline(true);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsOnline(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const navItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z" />
        </svg>
      ),
    },
    {
      label: "Investigation Workspace",
      href: "/workspace",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      ),
    },
    {
      label: "Run History",
      href: "/history",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex min-h-screen bg-[#09090B] text-[#F5F3EF]">
      {/* Sidebar Navigation (Desktop) */}
      <aside className="hidden md:flex w-64 flex-col border-r border-white/[0.08] bg-[#151519] shrink-0">
        {/* Brand identity block */}
        <div className="flex h-16 items-center justify-between border-b border-white/[0.08] px-5">
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-black/40 border border-[#F20B91]/60 text-[#F20B91] font-mono font-black text-sm tracking-tighter group-hover:border-[#D4FF32] group-hover:text-[#D4FF32] transition-colors">
              Ω
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="font-black tracking-tight text-[#F5F3EF] text-base group-hover:text-[#F20B91] transition-colors">
                ORACLE
              </span>
              <span className="font-mono text-[10px] text-[#85858D] font-bold">
                v0.1
              </span>
            </div>
          </Link>
          <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32] animate-pulse" title="System Ready" />
        </div>

        {/* Primary Action Button (Hot Pink) */}
        <div className="p-4 border-b border-white/[0.08]">
          <Link
            href="/diagnostics/new"
            className="flex items-center justify-center space-x-2 w-full rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-black px-4 py-2.5 text-xs transition-all tracking-wider shadow-[0_0_15px_rgba(242,11,145,0.3)] active:scale-[0.98]"
          >
            <svg className="w-3.5 h-3.5 stroke-[2.5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span>NEW DIAGNOSIS</span>
          </Link>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1 p-3 text-xs">
          <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest text-[#85858D] font-bold">
            Investigation Suite
          </div>
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-3 rounded px-3 py-2.5 transition-all ${
                  isActive
                    ? "bg-white/[0.05] text-[#F5F3EF] font-bold border-l-2 border-[#F20B91] pl-2.5"
                    : "text-[#85858D] hover:bg-white/[0.03] hover:text-[#F5F3EF]"
                }`}
              >
                <span className={isActive ? "text-[#F20B91]" : "text-[#85858D]"}>{item.icon}</span>
                <span className="tracking-tight">{item.label}</span>
              </Link>
            );
          })}

          <div className="pt-4 mt-4 border-t border-white/[0.08]">
            <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest text-[#85858D] font-bold">
              Overview
            </div>
            <Link
              href="/"
              className="flex items-center space-x-3 rounded px-3 py-2 text-[#85858D] hover:bg-white/[0.03] hover:text-[#F5F3EF] transition-colors"
            >
              <svg className="w-4 h-4 text-[#85858D]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span>Landing Page</span>
            </Link>
          </div>
        </nav>

        {/* Operational Status Panel */}
        <div className="border-t border-white/[0.08] p-4 text-[11px] space-y-2 bg-[#09090B] font-mono">
          <div className="text-[10px] uppercase font-bold tracking-widest text-[#85858D] mb-1">
            System Telemetry
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#85858D]">Gateway:</span>
            <div className="flex items-center space-x-1.5">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  isOnline === true ? "bg-[#D4FF32] shadow-[0_0_6px_rgba(212,255,50,0.8)]" : isOnline === false ? "bg-[#F20B91]" : "bg-[#85858D] animate-pulse"
                }`}
              />
              <span className={isOnline === true ? "text-[#D4FF32] font-bold" : "text-[#85858D]"}>
                {isOnline === true ? "8000 (Live)" : isOnline === false ? "Offline" : "Querying"}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#85858D]">Persistence:</span>
            <span className="font-bold">
              {status?.persistence_mode === "in_memory_transient" ? (
                <span className="text-[#85858D]" title="PostgreSQL offline; operating in memory-transient mode">
                  Transient
                </span>
              ) : status?.persistence_mode === "durable_postgresql" ? (
                <span className="text-[#D4FF32]">PostgreSQL</span>
              ) : (
                <span className="text-[#85858D]">Standby</span>
              )}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#85858D]">Dynamic Host:</span>
            <span className={`text-[10px] font-bold ${status?.docker_isolation_available ? "text-[#D4FF32]" : "text-[#85858D]"}`}>
              {status?.docker_isolation_available ? "Docker Sandbox" : "Gated (Safe)"}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="h-16 border-b border-white/[0.08] bg-[#151519]/90 backdrop-blur px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 rounded text-[#85858D] hover:text-[#F5F3EF]"
              aria-label="Toggle navigation"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Mobile Brand */}
            <Link href="/" className="md:hidden flex items-center space-x-2">
              <span className="font-mono text-[#F20B91] font-black text-base">Ω</span>
              <span className="font-black text-[#F5F3EF] tracking-tight">ORACLE</span>
            </Link>

            {activeTargetName && (
              <div className="flex items-center space-x-2 text-xs font-mono">
                <span className="text-[#85858D] hidden sm:inline">Active Target:</span>
                <span className="rounded bg-white/[0.04] border border-[#F20B91]/40 px-2 py-0.5 text-[#F5F3EF] font-bold">
                  {activeTargetName}
                </span>
              </div>
            )}
          </div>

          {/* Header Indicators */}
          <div className="flex items-center space-x-3 text-xs">
            <div className="hidden sm:flex items-center space-x-2 rounded border border-white/[0.08] bg-black/30 px-3 py-1 text-[11px] text-[#85858D] font-mono">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32] animate-pulse" />
              <span>Polyglot AST: Python • TS • Java • Go</span>
            </div>

            <Link
              href="/diagnostics/new"
              className="md:hidden flex items-center space-x-1.5 rounded bg-[#F20B91] hover:bg-[#d60a80] text-[#09090B] font-bold px-3 py-1.5 text-xs transition-colors"
            >
              <span>+ New</span>
            </Link>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-white/[0.08] bg-[#151519] p-4 space-y-2 text-xs">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center space-x-3 rounded px-3 py-2 text-[#F5F3EF] hover:bg-white/[0.05]"
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
            <Link
              href="/"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center space-x-3 rounded px-3 py-2 text-[#85858D] hover:bg-white/[0.05]"
            >
              <span>Landing Page</span>
            </Link>
          </div>
        )}

        {/* Content Body */}
        <main className="flex-1 overflow-auto bg-[#09090B] p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
