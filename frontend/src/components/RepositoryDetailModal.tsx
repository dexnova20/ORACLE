"use client";

import React, { useEffect } from "react";
import { Repository } from "@/types/api";

interface RepositoryDetailModalProps {
  repository: Repository | null;
  onClose: () => void;
}

export function RepositoryDetailModal({ repository, onClose }: RepositoryDetailModalProps) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!repository) {
    return null;
  }

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString();
    } catch {
      return isoString;
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-zinc-100 pb-4 dark:border-zinc-800">
          <div>
            <h3
              id="modal-title"
              className="text-lg font-semibold text-zinc-900 dark:text-zinc-100"
            >
              Diagnostic Target Details
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Registered repository metadata
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            aria-label="Close dialog"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        <dl className="mt-4 space-y-3 text-xs">
          <div>
            <dt className="font-medium text-zinc-500 dark:text-zinc-400">Repository Name</dt>
            <dd className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              {repository.name}
            </dd>
          </div>

          <div>
            <dt className="font-medium text-zinc-500 dark:text-zinc-400">Target UUID</dt>
            <dd className="mt-1 font-mono text-[11px] text-zinc-700 dark:text-zinc-300 select-all">
              {repository.id}
            </dd>
          </div>

          <div>
            <dt className="font-medium text-zinc-500 dark:text-zinc-400">Target Location / URL</dt>
            <dd className="mt-1 break-all rounded bg-zinc-50 p-2 font-mono text-zinc-800 dark:bg-zinc-800/60 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-750">
              {repository.url}
            </dd>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="font-medium text-zinc-500 dark:text-zinc-400">Source Type</dt>
              <dd className="mt-1">
                <span className="inline-flex items-center rounded-md bg-zinc-100 px-2 py-0.5 text-xs font-mono font-medium text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
                  {repository.source_type}
                </span>
              </dd>
            </div>
            <div>
              <dt className="font-medium text-zinc-500 dark:text-zinc-400">Status</dt>
              <dd className="mt-1">
                <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                  {repository.status}
                </span>
              </dd>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <div>
              <dt className="font-medium text-zinc-500 dark:text-zinc-400">Registered At</dt>
              <dd className="mt-1 text-zinc-700 dark:text-zinc-300">
                {formatDate(repository.created_at)}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-zinc-500 dark:text-zinc-400">Last Updated</dt>
              <dd className="mt-1 text-zinc-700 dark:text-zinc-300">
                {formatDate(repository.updated_at)}
              </dd>
            </div>
          </div>
        </dl>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-xs font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
