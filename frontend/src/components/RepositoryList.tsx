"use client";

import React, { useState } from "react";
import { deleteRepository } from "@/lib/api";
import { Repository } from "@/types/api";
import { RepositoryDetailModal } from "./RepositoryDetailModal";

interface RepositoryListProps {
  repositories: Repository[];
  loading: boolean;
  errorMessage: string | null;
  onRefresh: () => void;
  onDeleteSuccess: (deletedId: string) => void;
}

export function RepositoryList({
  repositories,
  loading,
  errorMessage,
  onRefresh,
  onDeleteSuccess,
}: RepositoryListProps) {
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [targetToDelete, setTargetToDelete] = useState<Repository | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const confirmDelete = async () => {
    if (!targetToDelete) return;
    setDeletingId(targetToDelete.id);
    setDeleteError(null);

    try {
      await deleteRepository(targetToDelete.id);
      const id = targetToDelete.id;
      setTargetToDelete(null);
      onDeleteSuccess(id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete repository registration.";
      setDeleteError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              Registered Diagnostic Targets
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Repositories registered in ORACLE catalog ({repositories.length})
            </p>
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-750"
          >
            {loading ? (
              <>
                <svg
                  className="mr-1.5 h-3.5 w-3.5 animate-spin"
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
                Refreshing...
              </>
            ) : (
              <>Refresh Targets</>
            )}
          </button>
        </div>

        {/* Global or List error message */}
        {errorMessage && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span>⚠️</span>
                <span>{errorMessage}</span>
              </div>
              <button
                onClick={onRefresh}
                className="font-medium underline hover:text-rose-950 dark:hover:text-rose-100"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && repositories.length === 0 && (
          <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center space-x-2 text-xs text-zinc-500">
              <span className="h-2 w-2 animate-ping rounded-full bg-zinc-400" />
              <span>Loading registered targets...</span>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && repositories.length === 0 && !errorMessage && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-zinc-200 p-8 text-center dark:border-zinc-800">
            <div className="rounded-full bg-zinc-100 p-3 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1.5"
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
            </div>
            <h3 className="mt-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              No diagnostic targets registered
            </h3>
            <p className="mt-1 max-w-sm text-xs text-zinc-500 dark:text-zinc-400">
              Use the registration form above to add repositories for future diagnostic analysis.
            </p>
          </div>
        )}

        {/* List of Repositories */}
        {repositories.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-200 text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <tr>
                  <th scope="col" className="pb-3 font-medium">Target Name</th>
                  <th scope="col" className="pb-3 font-medium">Location / URL</th>
                  <th scope="col" className="pb-3 font-medium">Source Type</th>
                  <th scope="col" className="pb-3 font-medium">Status</th>
                  <th scope="col" className="pb-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                {repositories.map((repo) => (
                  <tr key={repo.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30">
                    <td className="py-3 font-semibold text-zinc-900 dark:text-zinc-100">
                      {repo.name}
                    </td>
                    <td className="py-3 font-mono text-[11px] text-zinc-600 dark:text-zinc-400 max-w-xs truncate">
                      {repo.url}
                    </td>
                    <td className="py-3">
                      <span className="inline-flex items-center rounded-md bg-zinc-100 px-2 py-0.5 font-mono text-[11px] text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                        {repo.source_type}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                        {repo.status}
                      </span>
                    </td>
                    <td className="py-3 text-right space-x-2">
                      <button
                        onClick={() => setSelectedRepo(repo)}
                        className="rounded px-2 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
                      >
                        Details
                      </button>
                      <button
                        onClick={() => {
                          setDeleteError(null);
                          setTargetToDelete(repo);
                        }}
                        className="rounded px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50 hover:text-rose-800 dark:text-rose-400 dark:hover:bg-rose-950/30 dark:hover:text-rose-300"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Detail Modal */}
      <RepositoryDetailModal
        repository={selectedRepo}
        onClose={() => setSelectedRepo(null)}
      />

      {/* Delete Confirmation Modal */}
      {targetToDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-delete-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
        >
          <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
            <h3
              id="confirm-delete-title"
              className="text-base font-semibold text-zinc-900 dark:text-zinc-100"
            >
              Remove Target Registration?
            </h3>
            <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
              Are you sure you want to remove{" "}
              <strong className="text-zinc-900 dark:text-white">
                {targetToDelete.name}
              </strong>{" "}
              from the ORACLE catalog?
            </p>
            <p className="mt-2 rounded bg-zinc-50 p-2 text-[11px] text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
              Note: This action only removes the registration metadata record. Remote or local source code is never touched or deleted.
            </p>

            {deleteError && (
              <div className="mt-3 rounded border border-rose-200 bg-rose-50 p-2 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
                {deleteError}
              </div>
            )}

            <div className="mt-5 flex justify-end space-x-2">
              <button
                type="button"
                disabled={deletingId !== null}
                onClick={() => {
                  setTargetToDelete(null);
                  setDeleteError(null);
                }}
                className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletingId !== null}
                onClick={confirmDelete}
                className="inline-flex items-center rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-50 dark:bg-rose-700 dark:hover:bg-rose-600"
              >
                {deletingId ? "Removing..." : "Confirm Removal"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
