"""Static dependency graph representation with provenance tracking."""

from typing import Dict, List, Set
from pydantic import BaseModel, ConfigDict, Field

from oracle.inspection.ast_parser import ParsedFileSummary


class DependencyNode(BaseModel):
    """A node in the repository dependency graph."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable unique identifier for the node")
    label: str = Field(..., description="Human-readable node label (filename or module name)")
    node_type: str = Field(
        ...,
        description="Node category: source_file, internal_module, stdlib_module, external_package, unresolved_reference",
    )


class DependencyEdge(BaseModel):
    """A directed dependency relationship from a source file to an imported module/symbol."""

    model_config = ConfigDict(frozen=True)

    source_node: str = Field(..., description="Originating source file node ID")
    target_node: str = Field(..., description="Target dependency node ID")
    import_statement: str = Field(..., description="Raw import statement providing provenance")
    line_number: int = Field(..., ge=1, description="Line number of the import statement")
    dependency_type: str = Field(
        ...,
        description="Dependency type: stdlib, internal, external, unresolved",
    )
    is_resolved: bool = Field(..., description="Whether the dependency was resolved to a known module or file")


class DependencyGraph(BaseModel):
    """Immutable representation of the repository's static dependency graph."""

    model_config = ConfigDict(frozen=True)

    nodes: List[DependencyNode] = Field(default_factory=list, description="All graph nodes")
    edges: List[DependencyEdge] = Field(default_factory=list, description="All directed dependency edges")
    total_nodes: int = Field(default=0, ge=0)
    total_edges: int = Field(default=0, ge=0)
    internal_edge_count: int = Field(default=0, ge=0)
    external_edge_count: int = Field(default=0, ge=0)
    stdlib_edge_count: int = Field(default=0, ge=0)
    unresolved_edge_count: int = Field(default=0, ge=0)


def build_dependency_graph(parsed_summaries: List[ParsedFileSummary]) -> DependencyGraph:
    """Construct an aggregated dependency graph from parsed file summaries.

    Maintains full edge-level provenance (source file and line number for every edge).
    """
    node_map: Dict[str, DependencyNode] = {}
    edges: List[DependencyEdge] = []

    internal_count = 0
    external_count = 0
    stdlib_count = 0
    unresolved_count = 0

    # 1. Register all analyzed source file nodes
    for summary in parsed_summaries:
        file_id = f"file:{summary.file_path}"
        if file_id not in node_map:
            node_map[file_id] = DependencyNode(
                id=file_id,
                label=summary.file_path,
                node_type="source_file",
            )

        # 2. Register import targets and edges
        for imp in summary.imports:
            # Determine target node ID and type
            if imp.is_stdlib:
                target_id = f"stdlib:{imp.target_module}"
                node_type = "stdlib_module"
                dep_type = "stdlib"
                is_resolved = True
                stdlib_count += 1
            elif imp.is_internal:
                target_id = f"module:{imp.target_module}"
                node_type = "internal_module"
                dep_type = "internal"
                is_resolved = True
                internal_count += 1
            elif imp.resolution_status == "unresolved_reference":
                target_id = f"unresolved:{imp.target_module}"
                node_type = "unresolved_reference"
                dep_type = "unresolved"
                is_resolved = False
                unresolved_count += 1
            elif imp.resolution_status in ("unsupported_dynamic", "unsupported_resolution"):
                target_id = f"unsupported:{imp.target_module}"
                node_type = "unsupported_reference"
                dep_type = "unsupported"
                is_resolved = False
            else:
                if imp.target_module.startswith("pkg:"):
                    clean = imp.target_module[4:]
                    parts = clean.split(".")
                    if len(parts) >= 2 and parts[0] in ("org", "com", "io", "net", "ch", "androidx"):
                        pkg_group = ".".join(parts[:2])
                        target_id = f"pkg:{pkg_group}"
                    else:
                        target_id = f"pkg:{parts[0]}"
                else:
                    top_pkg = imp.target_module.split(".")[0]
                    target_id = f"pkg:{top_pkg}"
                node_type = "external_package"
                dep_type = "external"
                is_resolved = True
                external_count += 1

            if target_id not in node_map:
                node_map[target_id] = DependencyNode(
                    id=target_id,
                    label=imp.target_module,
                    node_type=node_type,
                )

            edges.append(
                DependencyEdge(
                    source_node=file_id,
                    target_node=target_id,
                    import_statement=imp.raw_statement,
                    line_number=imp.line_number,
                    dependency_type=dep_type,
                    is_resolved=is_resolved,
                )
            )

    sorted_nodes = sorted(node_map.values(), key=lambda n: n.id)
    sorted_edges = sorted(edges, key=lambda e: (e.source_node, e.line_number))

    return DependencyGraph(
        nodes=sorted_nodes,
        edges=sorted_edges,
        total_nodes=len(sorted_nodes),
        total_edges=len(sorted_edges),
        internal_edge_count=internal_count,
        external_edge_count=external_count,
        stdlib_edge_count=stdlib_count,
        unresolved_edge_count=unresolved_count,
    )
