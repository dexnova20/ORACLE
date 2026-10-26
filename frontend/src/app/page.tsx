"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { StatusCard } from "@/components/StatusCard";
import { HealthCheckAction } from "@/components/HealthCheckAction";
import { RepositoryRegistrationForm } from "@/components/RepositoryRegistrationForm";
import { RepositoryList } from "@/components/RepositoryList";
import { DiagnosticRunPanel } from "@/components/DiagnosticRunPanel";
import { DiagnosticWorkflowPreview } from "@/components/DiagnosticWorkflowPreview";
import { fetchStatus, listRepositories } from "@/lib/api";
import { SystemStatusResponse, AsyncState, Repository } from "@/types/api";

export default function HomePage() {
  const [statusState, setStatusState] = useState<AsyncState<SystemStatusResponse>>({
    state: "loading",
  });

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [reposLoading, setReposLoading] = useState<boolean>(true);
  const [reposError, setReposError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setStatusState({ state: "loading" });
    try {
      const data = await fetchStatus();
      setStatusState({
        state: "success",
        data,
        timestamp: new Date().toLocaleTimeString(),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend.";
      setStatusState({
        state: "error",
        error: msg,
        timestamp: new Date().toLocaleTimeString(),
      });
    }
  }, []);

  const loadRepositories = useCallback(async () => {
    setReposLoading(true);
    setReposError(null);
    try {
      const data = await listRepositories();
      setRepositories(data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to fetch registered repositories.";
      setReposError(msg);
    } finally {
      setReposLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    fetchStatus()
      .then((data) => {
        if (isMounted) {
          setStatusState({
            state: "success",
            data,
            timestamp: new Date().toLocaleTimeString(),
          });
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to connect to backend.";
          setStatusState({
            state: "error",
            error: msg,
            timestamp: new Date().toLocaleTimeString(),
          });
        }
      });

    listRepositories()
      .then((data) => {
        if (isMounted) {
          setRepositories(data);
          setReposLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error ? err.message : "Failed to fetch registered repositories.";
          setReposError(msg);
          setReposLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleRepositoryCreated = (newRepo: Repository) => {
    setRepositories((prev) => [newRepo, ...prev.filter((r) => r.id !== newRepo.id)]);
  };

  const handleRepositoryDeleted = (deletedId: string) => {
    setRepositories((prev) => prev.filter((r) => r.id !== deletedId));
  };

  const isBackendOnline =
    statusState.state === "success"
      ? true
      : statusState.state === "error"
      ? false
      : null;

  return (
    <div className="min-h-screen bg-zinc-50 font-sans text-zinc-900 antialiased dark:bg-black dark:text-zinc-100">
      <Navbar isOnline={isBackendOnline} />

      <main className="mx-auto max-w-6xl px-6 py-10 space-y-8">
        {/* Hero Section */}
        <section className="space-y-3">
          <div className="inline-flex items-center space-x-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-700 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span>Target Management Active</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-zinc-900 dark:text-white">
            ORACLE System Inspector
          </h1>
          <p className="max-w-3xl text-base text-zinc-600 dark:text-zinc-400">
            An extensible platform for inspecting software systems, identifying faults, testing
            components independently, and producing evidence-backed diagnoses.
          </p>
        </section>

        {/* Live System Status Section */}
        <StatusCard statusState={statusState} onRefresh={loadStatus} />

        {/* Diagnostic Targets Section */}
        <RepositoryRegistrationForm onSuccess={handleRepositoryCreated} />

        <RepositoryList
          repositories={repositories}
          loading={reposLoading}
          errorMessage={reposError}
          onRefresh={loadRepositories}
          onDeleteSuccess={handleRepositoryDeleted}
        />

        {/* End-to-End Diagnostic Pipeline */}
        <DiagnosticRunPanel repositories={repositories} />

        {/* On-Demand Health Check Section */}
        <HealthCheckAction />

        {/* Future Diagnostic Roadmap */}
        <DiagnosticWorkflowPreview />

        {/* Footer */}
        <footer className="border-t border-zinc-200 py-6 text-center text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-500">
          ORACLE Diagnostic Platform • Built with Next.js, TypeScript, Tailwind CSS &amp; FastAPI • Strictly PostgreSQL
        </footer>
      </main>
    </div>
  );
}

