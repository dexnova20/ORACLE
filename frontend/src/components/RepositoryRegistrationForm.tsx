"use client";

import React, { useState } from "react";
import { registerRepository } from "@/lib/api";
import { Repository, SourceType } from "@/types/api";

interface RepositoryRegistrationFormProps {
  onSuccess: (repository: Repository) => void;
}

const SUPPORTED_SCHEMES_REGEX = /^(https?|git|ssh|file):\/\//i;

export function RepositoryRegistrationForm({ onSuccess }: RepositoryRegistrationFormProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("git");

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const trimmedName = name.trim();
    const trimmedUrl = url.trim();

    if (!trimmedName) {
      setErrorMessage("Repository name cannot be empty.");
      return;
    }

    if (!trimmedUrl) {
      setErrorMessage("Repository URL cannot be empty.");
      return;
    }

    if (!SUPPORTED_SCHEMES_REGEX.test(trimmedUrl)) {
      setErrorMessage(
        "Invalid URL scheme. Must begin with https://, http://, git://, ssh://, or file://"
      );
      return;
    }

    // Check scheme-only input
    const remainder = trimmedUrl.replace(SUPPORTED_SCHEMES_REGEX, "").trim();
    if (!remainder) {
      setErrorMessage("Repository URL is incomplete or missing a host/path.");
      return;
    }

    setLoading(true);
    try {
      const created = await registerRepository({
        name: trimmedName,
        url: trimmedUrl,
        source_type: sourceType,
      });

      setSuccessMessage(`Registered diagnostic target "${created.name}" successfully.`);
      setName("");
      setUrl("");
      setSourceType("git");
      onSuccess(created);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to register repository target.";
      setErrorMessage(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-5">
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
          Register Diagnostic Target
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Register software repositories for upcoming diagnostic inspection. Source code is never cloned or executed during registration.
        </p>
      </div>

      {successMessage && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-300">
          <div className="flex items-center space-x-2">
            <span>✓</span>
            <span className="font-medium">{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-600 hover:text-emerald-800 dark:text-emerald-400 dark:hover:text-emerald-200"
          >
            ✕
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
          <div className="flex items-center space-x-2">
            <span>⚠️</span>
            <span className="font-medium">{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-600 hover:text-rose-800 dark:text-rose-400 dark:hover:text-rose-200"
          >
            ✕
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Target Name */}
          <div className="space-y-1.5">
            <label
              htmlFor="repo-name"
              className="block text-xs font-medium text-zinc-700 dark:text-zinc-300"
            >
              Target Name <span className="text-rose-500">*</span>
            </label>
            <input
              id="repo-name"
              type="text"
              required
              disabled={loading}
              placeholder="e.g. backend-api"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-xs text-zinc-900 placeholder-zinc-400 focus:border-zinc-500 focus:outline-hidden disabled:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:disabled:bg-zinc-900"
            />
          </div>

          {/* Source Type */}
          <div className="space-y-1.5">
            <label
              htmlFor="repo-source-type"
              className="block text-xs font-medium text-zinc-700 dark:text-zinc-300"
            >
              Source Type
            </label>
            <select
              id="repo-source-type"
              disabled={loading}
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as SourceType)}
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-xs text-zinc-900 focus:border-zinc-500 focus:outline-hidden disabled:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:disabled:bg-zinc-900"
            >
              <option value="git">Git Repository (git)</option>
              <option value="local_directory">Local Directory (local_directory)</option>
            </select>
          </div>
        </div>

        {/* Target URL */}
        <div className="space-y-1.5">
          <label
            htmlFor="repo-url"
            className="block text-xs font-medium text-zinc-700 dark:text-zinc-300"
          >
            Repository Location / URL <span className="text-rose-500">*</span>
          </label>
          <input
            id="repo-url"
            type="text"
            required
            disabled={loading}
            placeholder="e.g. https://github.com/organization/repo.git or file:///path/to/code"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 font-mono text-xs text-zinc-900 placeholder-zinc-400 focus:border-zinc-500 focus:outline-hidden disabled:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:disabled:bg-zinc-900"
          />
          <p className="text-[11px] text-zinc-400">
            Supported schemes: <code className="font-mono text-zinc-500 dark:text-zinc-300">https://</code>,{" "}
            <code className="font-mono text-zinc-500 dark:text-zinc-300">http://</code>,{" "}
            <code className="font-mono text-zinc-500 dark:text-zinc-300">git://</code>,{" "}
            <code className="font-mono text-zinc-500 dark:text-zinc-300">ssh://</code>,{" "}
            <code className="font-mono text-zinc-500 dark:text-zinc-300">file://</code>
          </p>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center rounded-lg bg-zinc-900 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {loading ? (
              <>
                <svg
                  className="mr-2 h-3.5 w-3.5 animate-spin"
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
                Registering Target...
              </>
            ) : (
              <>Register Target</>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
