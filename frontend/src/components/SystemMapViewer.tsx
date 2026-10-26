"use client";

import React, { useState } from "react";
import { DiagnosticSystemMap } from "@/types/api";

interface SystemMapViewerProps {
  systemMap: DiagnosticSystemMap;
}

export function SystemMapViewer({ systemMap }: SystemMapViewerProps) {
  const [filterType, setFilterType] = useState<string>("all");
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(
    systemMap.components.length > 0 ? systemMap.components[0].id : null
  );

  const filteredComponents = systemMap.components.filter((c) => {
    if (filterType === "all") return true;
    return c.component_type === filterType;
  });

  const selectedComponent = systemMap.components.find((c) => c.id === selectedComponentId);

  const outboundEdges = systemMap.edges.filter(
    (e) => e.source_component_id === selectedComponent?.id || e.source_component_id === `file:${selectedComponent?.file_path}`
  );

  const inboundEdges = systemMap.edges.filter(
    (e) => e.target_component_id === selectedComponent?.id
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "analyzed":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300";
      case "syntax_error":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
      case "unresolved":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300";
      default:
        return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "source_file":
        return "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300";
      case "internal_module":
        return "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300";
      case "external_package":
        return "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300";
      case "stdlib_module":
        return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
      case "unresolved_reference":
        return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300";
      default:
        return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
    }
  };

  return (
    <div className="space-y-4">
      {/* Metrics Bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/50">
          <div className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">Total Components</div>
          <div className="mt-1 text-xl font-bold text-zinc-900 dark:text-zinc-100">{systemMap.total_components}</div>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/50">
          <div className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">Dependency Edges</div>
          <div className="mt-1 text-xl font-bold text-zinc-900 dark:text-zinc-100">{systemMap.total_dependencies}</div>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/50">
          <div className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">Unresolved References</div>
          <div className={`mt-1 text-xl font-bold ${systemMap.unresolved_dependency_count > 0 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}>
            {systemMap.unresolved_dependency_count}
          </div>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/50">
          <div className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">Syntax Violations</div>
          <div className={`mt-1 text-xl font-bold ${systemMap.syntax_error_component_count > 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
            {systemMap.syntax_error_component_count}
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-zinc-200 pb-2 text-xs dark:border-zinc-800">
        {[
          { label: "All Nodes", value: "all" },
          { label: "Source Files", value: "source_file" },
          { label: "Internal Modules", value: "internal_module" },
          { label: "External Packages", value: "external_package" },
          { label: "Standard Library", value: "stdlib_module" },
          { label: "Unresolved References", value: "unresolved_reference" },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilterType(tab.value)}
            className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
              filterType === tab.value
                ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Explorer Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Component List */}
        <div className="max-h-96 overflow-y-auto rounded-lg border border-zinc-200 p-2 dark:border-zinc-800 lg:col-span-5">
          <div className="space-y-1">
            {filteredComponents.length === 0 ? (
              <div className="p-4 text-center text-xs text-zinc-400">No components match selected filter.</div>
            ) : (
              filteredComponents.map((comp) => (
                <button
                  key={comp.id}
                  onClick={() => setSelectedComponentId(comp.id)}
                  className={`w-full rounded-md p-2 text-left text-xs transition-colors ${
                    selectedComponentId === comp.id
                      ? "bg-zinc-100 font-medium text-zinc-950 dark:bg-zinc-800 dark:text-white"
                      : "hover:bg-zinc-50 dark:hover:bg-zinc-850 text-zinc-700 dark:text-zinc-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] truncate max-w-[200px]">{comp.name}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${getStatusBadge(comp.status)}`}>
                      {comp.status}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center space-x-1.5">
                    <span className={`rounded px-1 py-0.2 text-[9px] font-medium ${getTypeBadge(comp.component_type)}`}>
                      {comp.component_type}
                    </span>
                    {comp.file_path && (
                      <span className="font-mono text-[10px] text-zinc-400 truncate">{comp.file_path}</span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Selected Component Detail Inspector */}
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900 lg:col-span-7">
          {selectedComponent ? (
            <div className="space-y-4">
              <div className="border-b border-zinc-200 pb-3 dark:border-zinc-800">
                <div className="flex items-center justify-between">
                  <h4 className="font-mono text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    {selectedComponent.id}
                  </h4>
                  <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${getStatusBadge(selectedComponent.status)}`}>
                    {selectedComponent.status}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500">
                  <span>Type: <strong className="text-zinc-700 dark:text-zinc-300">{selectedComponent.component_type}</strong></span>
                  {selectedComponent.file_path && (
                    <span>Path: <strong className="text-zinc-700 dark:text-zinc-300">{selectedComponent.file_path}</strong></span>
                  )}
                </div>
              </div>

              {/* Outbound Dependencies */}
              <div>
                <h5 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Outbound Dependencies ({outboundEdges.length})
                </h5>
                <div className="mt-2 max-h-36 overflow-y-auto space-y-1">
                  {outboundEdges.length === 0 ? (
                    <div className="text-[11px] text-zinc-400 italic">No outbound dependency edges recorded.</div>
                  ) : (
                    outboundEdges.map((edge, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between rounded bg-zinc-50 p-1.5 font-mono text-[11px] dark:bg-zinc-950"
                      >
                        <div className="truncate max-w-xs">
                          <span className="text-zinc-400">imports </span>
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200">{edge.target_component_id}</span>
                          {edge.line_number && (
                            <span className="text-zinc-400"> (line {edge.line_number})</span>
                          )}
                        </div>
                        <span className={`rounded px-1.5 py-0.5 text-[9px] font-medium ${getTypeBadge(edge.dependency_type)}`}>
                          {edge.dependency_type}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Inbound Dependents */}
              <div>
                <h5 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Inbound Dependents ({inboundEdges.length})
                </h5>
                <div className="mt-2 max-h-36 overflow-y-auto space-y-1">
                  {inboundEdges.length === 0 ? (
                    <div className="text-[11px] text-zinc-400 italic">No inbound dependent components.</div>
                  ) : (
                    inboundEdges.map((edge, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between rounded bg-zinc-50 p-1.5 font-mono text-[11px] dark:bg-zinc-950"
                      >
                        <div className="truncate max-w-xs">
                          <span className="text-zinc-400">imported by </span>
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200">{edge.source_component_id}</span>
                        </div>
                        <span className="text-[10px] text-zinc-400">line {edge.line_number || "—"}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center text-xs text-zinc-400">
              Select a component node to inspect provenance and relationships.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
