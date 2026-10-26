import React from "react";
import { env } from "@/config/env";

interface NavbarProps {
  isOnline: boolean | null;
}

export function Navbar({ isOnline }: NavbarProps) {
  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 font-bold text-white shadow-sm dark:bg-zinc-100 dark:text-zinc-900">
            Ω
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-zinc-900 dark:text-white">
              ORACLE
            </span>
            <span className="ml-2 rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
              v0.1.0
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-xs">
          <span className="hidden font-mono text-zinc-500 sm:inline dark:text-zinc-400">
            API: {env.apiUrl}
          </span>
          <div className="flex items-center space-x-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                isOnline === true
                  ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                  : isOnline === false
                  ? "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]"
                  : "bg-amber-400 animate-pulse"
              }`}
            />
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {isOnline === true
                ? "Backend Reachable"
                : isOnline === false
                ? "Backend Unreachable"
                : "Checking Connection..."}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
