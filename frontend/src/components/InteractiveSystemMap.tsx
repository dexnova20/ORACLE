"use client";

import React, { useState } from "react";
import { DiagnosticSystemMap } from "@/types/api";

interface InteractiveSystemMapProps {
  systemMap?: DiagnosticSystemMap | null;
  highlightedComponentId?: string | null;
  onSelectComponent?: (componentId: string) => void;
  isDemo?: boolean;
}

// Sample architecture used strictly when demonstrating the landing page centerpiece
const DEMO_SYSTEM_MAP: DiagnosticSystemMap = {
  total_components: 6,
  total_dependencies: 7,
  internal_dependency_count: 3,
  external_dependency_count: 3,
  stdlib_edge_count: 0,
  unresolved_dependency_count: 1,
  syntax_error_component_count: 1,
  components: [
    {
      id: "comp:api_gateway",
      name: "api_gateway.py",
      component_type: "source_file",
      file_path: "src/api_gateway.py",
      status: "analyzed",
      metadata: { lines_of_code: 140, language: "python" },
    },
    {
      id: "comp:auth_service",
      name: "auth_service.ts",
      component_type: "source_file",
      file_path: "src/auth_service.ts",
      status: "syntax_error",
      metadata: { error: "Unexpected token ';' on line 42", language: "typescript" },
    },
    {
      id: "comp:user_repo",
      name: "UserRepository.java",
      component_type: "source_file",
      file_path: "src/main/java/UserRepository.java",
      status: "analyzed",
      metadata: { lines_of_code: 88, language: "java" },
    },
    {
      id: "comp:fastapi",
      name: "fastapi",
      component_type: "external_package",
      file_path: null,
      status: "analyzed",
      metadata: { ecosystem: "pypi" },
    },
    {
      id: "comp:postgres",
      name: "psycopg 3",
      component_type: "external_package",
      file_path: null,
      status: "analyzed",
      metadata: { ecosystem: "pypi" },
    },
    {
      id: "comp:unresolved_vault",
      name: "unresolved:secret_vault",
      component_type: "unresolved_reference",
      file_path: null,
      status: "unresolved",
      metadata: { missing_symbol: "secret_vault.Client" },
    },
  ],
  edges: [
    {
      source_component_id: "comp:api_gateway",
      target_component_id: "comp:fastapi",
      dependency_type: "external",
      line_number: 3,
      import_statement: "import fastapi",
      is_resolved: true,
      provenance: {},
    },
    {
      source_component_id: "comp:api_gateway",
      target_component_id: "comp:auth_service",
      dependency_type: "internal",
      line_number: 12,
      import_statement: "from services import auth",
      is_resolved: true,
      provenance: {},
    },
    {
      source_component_id: "comp:auth_service",
      target_component_id: "comp:user_repo",
      dependency_type: "internal",
      line_number: 8,
      import_statement: "import { UserRepository } from './UserRepository'",
      is_resolved: true,
      provenance: {},
    },
    {
      source_component_id: "comp:auth_service",
      target_component_id: "comp:unresolved_vault",
      dependency_type: "unresolved",
      line_number: 19,
      import_statement: "import { SecretVault } from 'secret_vault'",
      is_resolved: false,
      provenance: {},
    },
    {
      source_component_id: "comp:user_repo",
      target_component_id: "comp:postgres",
      dependency_type: "external",
      line_number: 4,
      import_statement: "import org.postgresql.Driver",
      is_resolved: true,
      provenance: {},
    },
  ],
};

export function InteractiveSystemMap({
  systemMap: inputSystemMap,
  highlightedComponentId,
  onSelectComponent,
  isDemo = false,
}: InteractiveSystemMapProps) {
  const mapData = inputSystemMap && inputSystemMap.components.length > 0 ? inputSystemMap : DEMO_SYSTEM_MAP;
  const isDisplayingSample = !inputSystemMap || inputSystemMap.components.length === 0 || isDemo;

  const [selectedId, setSelectedId] = useState<string | null>(
    highlightedComponentId || (mapData.components.length > 0 ? mapData.components[0].id : null)
  );

  const activeId = highlightedComponentId || selectedId;
  const selectedNode = mapData.components.find((c) => c.id === activeId);

  const connectedTargetIds = new Set(
    mapData.edges
      .filter((e) => e.source_component_id === activeId || e.source_component_id === `file:${selectedNode?.file_path}`)
      .map((e) => e.target_component_id)
  );

  const connectedSourceIds = new Set(
    mapData.edges
      .filter((e) => e.target_component_id === activeId)
      .map((e) => e.source_component_id)
  );

  const handleNodeClick = (id: string) => {
    setSelectedId(id);
    if (onSelectComponent) {
      onSelectComponent(id);
    }
  };

  const getStatusStyles = (status: string, isHighlighted: boolean) => {
    if (isHighlighted) {
      return "border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-[0_0_15px_rgba(34,211,238,0.25)] ring-2 ring-cyan-400/40";
    }
    switch (status) {
      case "syntax_error":
        return "border-rose-500/80 bg-rose-950/20 text-rose-300 hover:border-rose-400";
      case "unresolved":
        return "border-amber-500/80 bg-amber-950/20 text-amber-300 hover:border-amber-400";
      case "blocked":
        return "border-purple-500/80 bg-purple-950/20 text-purple-300 hover:border-purple-400";
      case "analyzed":
      default:
        return "border-slate-800 bg-[#0d1424] text-slate-300 hover:border-slate-600";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "syntax_error":
        return { text: "Syntax Error", bg: "bg-rose-500/20 text-rose-400 border-rose-500/30" };
      case "unresolved":
        return { text: "Unresolved", bg: "bg-amber-500/20 text-amber-400 border-amber-500/30" };
      case "blocked":
        return { text: "Blocked", bg: "bg-purple-500/20 text-purple-400 border-purple-500/30" };
      case "analyzed":
      default:
        return { text: "Analyzed", bg: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" };
    }
  };

  return (
    <div className="flex flex-col h-full rounded-xl border border-slate-800/80 bg-[#0a0f1d] overflow-hidden">
      {/* Map Header & Controls */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800/80 px-4 py-3 bg-[#0d1322]/80 gap-2 shrink-0">
        <div className="flex items-center space-x-2">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-cyan-500/10 text-cyan-400">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            System Dependency Graph
          </span>
          {isDisplayingSample && (
            <span className="rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
              Interactive Demo Model
            </span>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 text-[11px]">
          <span className="flex items-center space-x-1 text-slate-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>Analyzed</span>
          </span>
          <span className="flex items-center space-x-1 text-slate-400">
            <span className="h-2 w-2 rounded-full bg-rose-400" />
            <span>Syntax Defect</span>
          </span>
          <span className="flex items-center space-x-1 text-slate-400">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            <span>Unresolved</span>
          </span>
        </div>
      </div>

      {/* Graph Area */}
      <div className="p-4 sm:p-5 flex-1 overflow-auto space-y-4">
        {/* Component Nodes Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {mapData.components.map((comp) => {
            const isSelected = comp.id === activeId;
            const isConnected = connectedTargetIds.has(comp.id) || connectedSourceIds.has(comp.id);
            const badge = getStatusBadge(comp.status);

            return (
              <button
                key={comp.id}
                onClick={() => handleNodeClick(comp.id)}
                className={`text-left p-3.5 rounded-lg border transition-all relative group cursor-pointer ${getStatusStyles(
                  comp.status,
                  isSelected
                )} ${isConnected && !isSelected ? "ring-1 ring-cyan-500/30" : ""}`}
              >
                <div className="flex items-start justify-between gap-1.5 mb-1.5">
                  <span className="font-mono text-xs font-bold truncate max-w-[170px]" title={comp.name}>
                    {comp.name}
                  </span>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border shrink-0 ${badge.bg}`}>
                    {badge.text}
                  </span>
                </div>

                <div className="text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>{comp.component_type.replace("_", " ")}</span>
                  {comp.metadata?.language ? (
                    <span className="text-slate-500 uppercase text-[9px] font-bold">
                      {String(comp.metadata.language)}
                    </span>
                  ) : null}
                </div>

                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                )}
              </button>
            );
          })}
        </div>

        {/* Selected Component Inspection & Dependency Details */}
        {selectedNode && (
          <div className="mt-4 rounded-lg border border-slate-800 bg-[#0d1322] p-4 text-xs space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
              <div className="flex items-center space-x-2">
                <span className="font-mono font-bold text-cyan-300">{selectedNode.name}</span>
                <span className="text-[10px] text-slate-400 font-mono">({selectedNode.id})</span>
              </div>
              <span className="text-[11px] text-slate-400">
                {selectedNode.file_path || "External Package"}
              </span>
            </div>

            {/* Outgoing & Incoming Edges */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
                  Depends On ({mapData.edges.filter((e) => e.source_component_id === selectedNode.id).length}):
                </span>
                <ul className="space-y-1 font-mono text-[11px]">
                  {mapData.edges
                    .filter((e) => e.source_component_id === selectedNode.id)
                    .map((edge, idx) => (
                      <li key={idx} className="flex items-center space-x-1.5 text-slate-300">
                        <span className="text-cyan-400">→</span>
                        <span className="truncate">{edge.target_component_id.replace("comp:", "")}</span>
                        <span className="text-[10px] text-slate-500">({edge.dependency_type})</span>
                      </li>
                    ))}
                  {mapData.edges.filter((e) => e.source_component_id === selectedNode.id).length === 0 && (
                    <li className="text-slate-500 italic">No outgoing dependencies</li>
                  )}
                </ul>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
                  Depended On By ({mapData.edges.filter((e) => e.target_component_id === selectedNode.id).length}):
                </span>
                <ul className="space-y-1 font-mono text-[11px]">
                  {mapData.edges
                    .filter((e) => e.target_component_id === selectedNode.id)
                    .map((edge, idx) => (
                      <li key={idx} className="flex items-center space-x-1.5 text-slate-300">
                        <span className="text-violet-400">←</span>
                        <span className="truncate">{edge.source_component_id.replace("comp:", "")}</span>
                      </li>
                    ))}
                  {mapData.edges.filter((e) => e.target_component_id === selectedNode.id).length === 0 && (
                    <li className="text-slate-500 italic">Root entrypoint / independent component</li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Metrics */}
      <div className="border-t border-slate-800/80 px-4 py-2 bg-[#090e1a] text-[11px] text-slate-400 flex items-center justify-between font-mono shrink-0">
        <span>Nodes: {mapData.total_components}</span>
        <span>Edges: {mapData.total_dependencies}</span>
        <span className={mapData.unresolved_dependency_count > 0 ? "text-amber-400" : "text-emerald-400"}>
          Unresolved: {mapData.unresolved_dependency_count}
        </span>
        <span className={mapData.syntax_error_component_count > 0 ? "text-rose-400" : "text-emerald-400"}>
          Syntax Defect: {mapData.syntax_error_component_count}
        </span>
      </div>
    </div>
  );
}
