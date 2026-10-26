"""Static language and project ecosystem detection based on repository manifests and source extensions."""

import os
from typing import Any, Dict, List, Set
from pydantic import BaseModel, ConfigDict, Field


class DetectedEcosystem(BaseModel):
    """Represents a detected software language ecosystem within a repository."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Ecosystem identifier (e.g. python, typescript, java_jvm, c_cpp)")
    title: str = Field(..., description="Human-readable ecosystem name")
    confidence: str = Field(..., description="Detection strength: high (manifest found), medium (source files only)")
    manifest_files: List[str] = Field(default_factory=list, description="Discovered configuration/build manifest files")
    source_file_count: int = Field(default=0, description="Count of identified source files in this ecosystem")
    sample_evidence: List[str] = Field(default_factory=list, description="Key files providing evidence of this ecosystem")


# Deterministic marker definitions for supported ecosystems
ECOSYSTEM_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "python": {
        "title": "Python Ecosystem",
        "manifest_names": {
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "setup.cfg",
            "Pipfile",
            "Pipfile.lock",
            "environment.yml",
            "tox.ini",
        },
        "source_extensions": {".py", ".pyi"},
    },
    "javascript_typescript": {
        "title": "JavaScript / TypeScript Ecosystem",
        "manifest_names": {
            "package.json",
            "tsconfig.json",
            "jsconfig.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "bun.lockb",
        },
        "source_extensions": {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"},
    },
    "java_jvm": {
        "title": "Java / JVM Ecosystem",
        "manifest_names": {
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
            "mvnw",
            "gradlew",
        },
        "source_extensions": {".java", ".kt", ".kts", ".scala"},
    },
    "go": {
        "title": "Go Ecosystem",
        "manifest_names": {
            "go.mod",
            "go.sum",
            "go.work",
        },
        "source_extensions": {".go"},
    },
    "c_cpp": {
        "title": "C / C++ Ecosystem",
        "manifest_names": {
            "CMakeLists.txt",
            "Makefile",
            "makefile",
            "meson.build",
            "configure.ac",
            "Kbuild",
        },
        "source_extensions": {".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx", ".hh"},
    },
}


def detect_ecosystems(discovered_relative_files: List[str]) -> List[DetectedEcosystem]:
    """Analyze discovered relative file paths to detect active programming ecosystems.

    Pure deterministic inspection of paths; executes no external binaries or scripts.
    Supports mixed-language repositories by evaluating each ecosystem independently.
    """
    detected: List[DetectedEcosystem] = []

    # Map files by basename and extension for fast lookups
    file_basenames = {os.path.basename(f): f for f in discovered_relative_files}
    files_by_ext: Dict[str, List[str]] = {}
    for f in discovered_relative_files:
        _, ext = os.path.splitext(f)
        ext_lower = ext.lower()
        if ext_lower:
            files_by_ext.setdefault(ext_lower, []).append(f)

    for eco_key, spec in ECOSYSTEM_DEFINITIONS.items():
        matched_manifests: List[str] = []
        for manifest_name in spec["manifest_names"]:
            # Check if any discovered file matches the manifest basename
            matching = [f for f in discovered_relative_files if os.path.basename(f) == manifest_name]
            matched_manifests.extend(matching)

        matched_source_count = 0
        sample_sources: List[str] = []
        for ext in spec["source_extensions"]:
            matching_sources = files_by_ext.get(ext, [])
            matched_source_count += len(matching_sources)
            sample_sources.extend(matching_sources[:3])

        if matched_manifests or matched_source_count > 0:
            confidence = "high" if matched_manifests else "medium"
            evidence = (matched_manifests + sample_sources)[:5]

            detected.append(
                DetectedEcosystem(
                    name=eco_key,
                    title=spec["title"],
                    confidence=confidence,
                    manifest_files=sorted(matched_manifests),
                    source_file_count=matched_source_count,
                    sample_evidence=sorted(evidence),
                )
            )

    # Sort ecosystems by source file count descending
    detected.sort(key=lambda e: (e.confidence == "high", e.source_file_count), reverse=True)
    return detected
