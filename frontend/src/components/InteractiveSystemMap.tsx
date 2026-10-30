"use client";

import React, { useState } from "react";
import { DiagnosticSystemMap } from "@/types/api";

interface InteractiveSystemMapProps {
  systemMap?: DiagnosticSystemMap | null;
  highlightedComponentId?: string | null;
  onSelectComponent?: (componentId: string) => void;
  isDemo?: boolean;
}

// Canonical demo system topology with realistic failure injection
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
      metadata: { lines_of_code: 140, language: "python", role: "HTTP Entrypoint" },
    },
    {
      id: "comp:auth_service",
      name: "auth_service.ts",
      component_type: "source_file",
      file_path: "src/auth_service.ts",
      status: "syntax_error",
      metadata: { error: "Unexpected token ';' on line 42", language: "typescript", role: "Token Validator" },
    },
    {
      id: "comp:user_repo",
      name: "UserRepository.java",
      component_type: "source_file",
      file_path: "src/main/java/UserRepository.java",
      status: "analyzed",
      metadata: { lines_of_code: 88, language: "java", role: "Data Persistence" },
    },
    {
      id: "comp:fastapi",
      name: "fastapi",
      component_type: "external_package",
      file_path: null,
      status: "analyzed",
      metadata: { ecosystem: "pypi", version: "0.115.0" },
    },
    {
      id: "comp:postgres",
      name: "psycopg3",
      component_type: "external_package",
      file_path: null,
      status: "analyzed",
      metadata: { ecosystem: "pypi", version: "3.2.1" },
    },
    {
      id: "comp:unresolved_vault",
      name: "unresolved:secret_vault",
      component_type: "unresolved_reference",
      file_path: null,
      status: "unresolved",
      metadata: { missing_symbol: "secret_vault.Client", reason: "Missing module declaration" },
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
      dependency_type: "internal",
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

const CANVAS_POSITIONS: Record<string, { x: number; y: number }> = {
  "comp:api_gateway": { x: 50, y: 15 },
  "comp:fastapi": { x: 18, y: 15 },
  "comp:auth_service": { x: 50, y: 52 },
  "comp:user_repo": { x: 82, y: 52 },
  "comp:unresolved_vault": { x: 18, y: 82 },
  "comp:postgres": { x: 82, y: 82 },
};

export function InteractiveSystemMap({
  systemMap,
  highlightedComponentId,
  onSelectComponent,
  isDemo = false,
}: InteractiveSystemMapProps) {
  const [selectedCompId, setSelectedCompId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"graph" | "matrix">("graph");

  const mapData = systemMap && systemMap.components.length > 0 ? systemMap : isDemo ? DEMO_SYSTEM_MAP : null;
  const activeId = highlightedComponentId || selectedCompId;

  if (!mapData || mapData.components.length === 0) {
    return (
      <div className="flex h-full min-h-[360px] flex-col items-center justify-center rounded border border-white/[0.08] bg-[#151519] p-6 text-center font-mono text-xs text-[#85858D]">
        <div className="h-8 w-8 rounded-full border border-white/[0.1] bg-black/40 flex items-center justify-center text-[#85858D] mb-3">
          ∅
        </div>
        <p className="font-bold text-[#F5F3EF]">No System Topology Available</p>
        <p className="text-[11px] text-[#85858D] mt-1 max-w-xs">
          Execute a diagnostic run against an analyzed codebase to assemble an interactive AST dependency graph.
        </p>
      </div>
    );
  }

  const handleNodeClick = (compId: string) => {
    const nextId = compId === selectedCompId ? null : compId;
    setSelectedCompId(nextId);
    if (onSelectComponent) {
      onSelectComponent(nextId || "");
    }
  };

  const selectedComponent = mapData.components.find((c) => c.id === activeId);

  // Compute connected nodes for highlighted component
  const connectedTargetIds = new Set(
    mapData.edges
      .filter((e) => e.source_component_id === activeId)
      .map((e) => e.target_component_id)
  );
  const connectedSourceIds = new Set(
    mapData.edges
      .filter((e) => e.target_component_id === activeId)
      .map((e) => e.source_component_id)
  );

  const getNodeColor = (status: string, isSelected: boolean) => {
    if (status === "syntax_error") {
      return {
        border: "border-[#F20B91]",
        bg: isSelected ? "bg-[#F20B91]/20" : "bg-black/70",
        dot: "bg-[#F20B91]",
        badge: "text-[#F20B91] bg-black border-[#F20B91]/60",
      };
    }
    if (status === "unresolved") {
      return {
        border: "border-[#D4FF32]/60",
        bg: isSelected ? "bg-[#D4FF32]/15" : "bg-black/70",
        dot: "bg-[#D4FF32]",
        badge: "text-[#D4FF32] bg-black border-[#D4FF32]/50",
      };
    }
    return {
      border: isSelected ? "border-[#D4FF32]" : "border-white/[0.1]",
      bg: isSelected ? "bg-[#151519]" : "bg-[#151519]",
      dot: "bg-[#D4FF32]",
      badge: "text-[#D4FF32] bg-black border-[#D4FF32]/30",
    };
  };

  return (
    <div className="flex flex-col h-full rounded border border-white/[0.08] bg-[#151519] overflow-hidden">
      {/* Header bar */}
      <div className="border-b border-white/[0.08] px-4 py-2.5 bg-[#09090B] flex items-center justify-between shrink-0 font-mono text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-[#D4FF32] font-black">◈</span>
          <span className="font-bold uppercase tracking-wider text-[#F5F3EF]">
            System Architecture Topology
          </span>
          <span className="text-[10px] text-[#85858D] hidden sm:inline">
            ({mapData.components.length} nodes • {mapData.edges.length} edges)
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* View mode toggle */}
          <div className="flex items-center rounded border border-white/[0.08] bg-black/40 p-0.5 text-[11px] font-mono">
            <button
              onClick={() => setViewMode("graph")}
              className={`px-2 py-0.5 rounded transition-colors ${
                viewMode === "graph" ? "bg-white/[0.1] text-[#D4FF32] font-bold" : "text-[#85858D] hover:text-[#F5F3EF]"
              }`}
            >
              Canvas View
            </button>
            <button
              onClick={() => setViewMode("matrix")}
              className={`px-2 py-0.5 rounded transition-colors ${
                viewMode === "matrix" ? "bg-white/[0.1] text-[#D4FF32] font-bold" : "text-[#85858D] hover:text-[#F5F3EF]"
              }`}
            >
              Matrix Table
            </button>
          </div>

          {/* Micro Legend */}
          <div className="hidden sm:flex items-center space-x-2 text-[10px] font-mono text-[#85858D]">
            <span className="flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32]" />
              <span>Clean</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[#F20B91]" />
              <span>Fault</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[#D4FF32]/80" />
              <span>Unresolved</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main visualization container */}
      <div className="flex-1 relative overflow-auto p-4 flex flex-col justify-between min-h-[360px] bg-[#09090B]">
        {viewMode === "graph" ? (
          <div className="relative w-full h-full min-h-[300px] bg-[#09090B] bg-grid-pattern rounded border border-white/[0.06] p-3 flex flex-col justify-between overflow-hidden">
            {/* SVG Link Layer */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
              <defs>
                <linearGradient id="edge-chartreuse" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#D4FF32" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#D4FF32" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="edge-fault" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#F20B91" stopOpacity="0.85" />
                  <stop offset="100%" stopColor="#F20B91" stopOpacity="0.3" />
                </linearGradient>
              </defs>

              {/* Render dynamic dependency lines */}
              {mapData.edges.map((edge, idx) => {
                const srcPos = CANVAS_POSITIONS[edge.source_component_id] || { x: 30 + (idx * 15) % 60, y: 20 + idx * 10 };
                const tgtPos = CANVAS_POSITIONS[edge.target_component_id] || { x: 40 + (idx * 12) % 50, y: 70 - idx * 8 };

                const isConnectedToActive =
                  edge.source_component_id === activeId ||
                  edge.target_component_id === activeId;

                const isFaultPath =
                  edge.source_component_id === "comp:auth_service" ||
                  edge.target_component_id === "comp:auth_service";

                return (
                  <g key={`edge-${idx}`}>
                    <line
                      x1={`${srcPos.x}%`}
                      y1={`${srcPos.y}%`}
                      x2={`${tgtPos.x}%`}
                      y2={`${tgtPos.y}%`}
                      stroke={
                        isFaultPath
                          ? "url(#edge-fault)"
                          : isConnectedToActive
                          ? "#D4FF32"
                          : "#85858D"
                      }
                      strokeWidth={isConnectedToActive || isFaultPath ? "2" : "1"}
                      strokeOpacity={isConnectedToActive || isFaultPath ? 1 : 0.25}
                      strokeDasharray={isConnectedToActive ? "4 4" : undefined}
                      className={isConnectedToActive ? "animate-flow-edge" : undefined}
                    />
                    {/* Direction particle marker */}
                    <circle
                      cx={`${(srcPos.x + tgtPos.x) / 2}%`}
                      cy={`${(srcPos.y + tgtPos.y) / 2}%`}
                      r={isConnectedToActive ? "3" : "1.75"}
                      fill={isFaultPath ? "#F20B91" : isConnectedToActive ? "#D4FF32" : "#85858D"}
                    />
                  </g>
                );
              })}
            </svg>

            {/* Visual Node Coordinates Grid */}
            <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 w-full">
              {mapData.components.map((comp) => {
                const isSelected = comp.id === activeId;
                const isConnected = connectedTargetIds.has(comp.id) || connectedSourceIds.has(comp.id);
                const colors = getNodeColor(comp.status, isSelected);

                return (
                  <button
                    key={comp.id}
                    onClick={() => handleNodeClick(comp.id)}
                    className={`text-left p-3.5 rounded border transition-all text-xs cursor-pointer ${colors.border} ${colors.bg} ${
                      isSelected
                        ? "shadow-[0_0_15px_rgba(242,11,145,0.25)] ring-1 ring-[#F20B91]"
                        : isConnected
                        ? "border-[#D4FF32]/60"
                        : "hover:border-white/[0.25]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center space-x-2 truncate">
                        <span className={`h-2 w-2 rounded-full ${colors.dot}`} />
                        <span className="font-mono font-bold text-[#F5F3EF] truncate text-[11px]" title={comp.name}>
                          {comp.name}
                        </span>
                      </div>
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border ${colors.badge}`}>
                        {comp.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-[#85858D] font-mono">
                      <span>{comp.component_type}</span>
                      {comp.metadata?.language ? (
                        <span className="text-[#D4FF32] font-black uppercase">{String(comp.metadata.language)}</span>
                      ) : comp.metadata?.ecosystem ? (
                        <span className="text-[#85858D] uppercase font-bold">{String(comp.metadata.ecosystem)}</span>
                      ) : null}
                    </div>

                    {Boolean(comp.metadata?.error) && (
                      <div className="mt-1.5 text-[10px] font-mono text-[#F20B91] truncate font-bold" title={String(comp.metadata.error)}>
                        ⚠ {String(comp.metadata.error)}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Hint bar at bottom */}
            <div className="relative z-10 flex items-center justify-between pt-3 text-[10px] font-mono text-[#85858D] border-t border-white/[0.06] mt-4">
              <span>Click a node to inspect call graph &amp; filter evidence</span>
              {activeId && (
                <button
                  onClick={() => setSelectedCompId(null)}
                  className="text-[#D4FF32] hover:underline cursor-pointer font-bold"
                >
                  Clear Selection (ESC)
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Matrix Table View */
          <div className="overflow-x-auto rounded border border-white/[0.08] bg-[#151519] p-2 font-mono text-xs">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-white/[0.08] text-[10px] text-[#85858D] uppercase tracking-wider bg-[#09090B]">
                <tr>
                  <th className="px-3 py-2">Component Node</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Outbound Imports</th>
                  <th className="px-3 py-2">Inbound Dependents</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {mapData.components.map((comp) => {
                  const outCount = mapData.edges.filter((e) => e.source_component_id === comp.id).length;
                  const inCount = mapData.edges.filter((e) => e.target_component_id === comp.id).length;
                  const isSelected = comp.id === activeId;

                  return (
                    <tr
                      key={comp.id}
                      onClick={() => handleNodeClick(comp.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? "bg-white/[0.08] text-[#F5F3EF]" : "hover:bg-white/[0.02] text-[#85858D]"
                      }`}
                    >
                      <td className="px-3 py-2 font-bold text-[#F5F3EF] flex items-center space-x-2">
                        <span className={`h-1.5 w-1.5 rounded-full ${comp.status === "syntax_error" ? "bg-[#F20B91]" : "bg-[#D4FF32]"}`} />
                        <span>{comp.name}</span>
                      </td>
                      <td className="px-3 py-2 text-[#85858D]">{comp.component_type}</td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                          comp.status === "syntax_error"
                            ? "border-[#F20B91]/50 bg-black text-[#F20B91] font-bold"
                            : "border-white/[0.1] text-[#D4FF32]"
                        }`}>
                          {comp.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-[#85858D]">{outCount} edges</td>
                      <td className="px-3 py-2 text-[#85858D]">{inCount} callers</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Selected Component Detail Drawer */}
        {selectedComponent && (
          <div className="mt-3 rounded border border-white/[0.08] bg-[#151519] p-3 text-xs font-mono space-y-2">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-1.5">
              <div className="flex items-center space-x-2">
                <span className="text-[#D4FF32] font-black">{selectedComponent.name}</span>
                <span className="text-[10px] text-[#85858D]">({selectedComponent.id})</span>
              </div>
              <button
                onClick={() => setSelectedCompId(null)}
                className="text-[#85858D] hover:text-[#F5F3EF] text-xs cursor-pointer font-bold"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-[#85858D]">
              <div>
                <span className="text-[#85858D] block text-[10px] uppercase font-bold">File Location:</span>
                <span className="text-[#F5F3EF]">{selectedComponent.file_path || "External Package"}</span>
              </div>
              <div>
                <span className="text-[#85858D] block text-[10px] uppercase font-bold">Status Assessment:</span>
                <span className={selectedComponent.status === "syntax_error" ? "text-[#F20B91] font-bold" : "text-[#D4FF32] font-bold"}>
                  {selectedComponent.status}
                </span>
              </div>
            </div>

            {selectedComponent.metadata && (
              <div className="pt-1 text-[11px] text-[#85858D] border-t border-white/[0.06]">
                <pre className="p-2 rounded bg-black/60 overflow-x-auto text-[10px] text-[#F5F3EF]">
                  {JSON.stringify(selectedComponent.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
