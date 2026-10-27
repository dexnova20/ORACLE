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
    { label: "Dashboard", href: "/dashboard", icon: "dashboard" },
    { label: "Workspace", href: "/workspace", icon: "workspace" },
    { label: "Run History", href: "/history", icon: "history" },
  ];

  return (
    <div className="flex min-h-screen bg-[#070a12] text-slate-200">
      {/* Sidebar Navigation */}
      <aside className="hidden md:flex w-64 flex-col border-r border-slate-800/80 bg-[#0a0f1d] shrink-0">
        {/* Brand */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800/80 px-5">
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 font-bold text-white shadow-md shadow-cyan-500/20 text-sm">
              Ω
            </div>
            <div>
              <span className="font-bold text-slate-100 tracking-tight text-base group-hover:text-cyan-400 transition-colors">
                ORACLE
              </span>
              <span className="ml-1.5 rounded bg-cyan-950/80 border border-cyan-800/60 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-cyan-300">
                v0.1
              </span>
            </div>
          </Link>
        </div>

        {/* Primary Action */}
        <div className="p-4 border-b border-slate-800/60">
          <Link
            href="/diagnostics/new"
            className="flex items-center justify-center space-x-2 w-full rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-4 py-2.5 text-xs transition-all shadow-sm shadow-cyan-500/20 active:scale-[0.98]"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span>New Diagnosis</span>
          </Link>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1.5 p-4 text-xs font-medium">
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-3 rounded-lg px-3 py-2.5 transition-all ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-semibold"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`}
              >
                {item.icon === "dashboard" && (
                  <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                )}
                {item.icon === "workspace" && (
                  <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                )}
                {item.icon === "history" && (
                  <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                <span>{item.label}</span>
              </Link>
            );
          })}

          <div className="pt-4 border-t border-slate-800/60">
            <Link
              href="/"
              className="flex items-center space-x-3 rounded-lg px-3 py-2 text-slate-400 hover:bg-slate-800/40 hover:text-slate-200 transition-colors"
            >
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span>Landing Page</span>
            </Link>
          </div>
        </nav>

        {/* Operational Status Footer */}
        <div className="border-t border-slate-800/80 p-4 text-[11px] space-y-2.5 bg-[#080d19]">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-medium">Gateway:</span>
            <div className="flex items-center space-x-1.5">
              <span
                className={`h-2 w-2 rounded-full ${
                  isOnline === true ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" : isOnline === false ? "bg-rose-500" : "bg-amber-400 animate-pulse"
                }`}
              />
              <span className="font-mono text-slate-300">
                {isOnline === true ? "127.0.0.1:8000" : isOnline === false ? "Offline" : "Checking..."}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-medium">Persistence:</span>
            <span className="font-mono font-semibold text-slate-300">
              {status?.persistence_mode === "in_memory_transient" ? (
                <span className="text-amber-400" title="PostgreSQL offline; operating in memory-transient mode">
                  Transient Mem
                </span>
              ) : status?.persistence_mode === "durable_postgresql" ? (
                <span className="text-emerald-400">PostgreSQL</span>
              ) : (
                <span className="text-slate-500">Standby</span>
              )}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-medium">Docker Sandbox:</span>
            <span className={`font-mono text-[10px] font-semibold ${status?.docker_isolation_available ? "text-emerald-400" : "text-slate-500"}`}>
              {status?.docker_isolation_available ? "Available" : "Disabled (Safe)"}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="h-16 border-b border-slate-800/80 bg-[#0a0f1d]/90 backdrop-blur px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            {/* Mobile Brand / Menu link */}
            <Link href="/" className="md:hidden flex items-center space-x-2">
              <div className="flex h-7 w-7 items-center justify-center rounded bg-cyan-500 text-slate-950 font-bold text-xs">
                Ω
              </div>
              <span className="font-bold text-slate-100">ORACLE</span>
            </Link>

            {activeTargetName && (
              <div className="flex items-center space-x-2 text-xs font-mono">
                <span className="text-slate-500 hidden sm:inline">Active Target:</span>
                <span className="rounded bg-slate-800/80 border border-slate-700/80 px-2 py-0.5 text-cyan-300 font-semibold">
                  {activeTargetName}
                </span>
              </div>
            )}
          </div>

          {/* Quick links & Status */}
          <div className="flex items-center space-x-3 text-xs">
            <div className="hidden sm:flex items-center space-x-2 rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>Polyglot Engine: Python, TS, Java, Go</span>
            </div>

            <Link
              href="/diagnostics/new"
              className="md:hidden flex items-center space-x-1.5 rounded-md bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-3 py-1.5 text-xs transition-colors"
            >
              <span>+ New</span>
            </Link>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 overflow-auto bg-[#070a12] p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
