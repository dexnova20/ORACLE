"""Project-aware and scenario-aware dataset splitting strategies.

Random train/test splits cause severe target/group data leakage in software diagnostics:
a model trained on cases from project A will memorize project-specific log phrases,
path layouts, and dependency names, yielding artificially high test accuracy that collapses
when deployed on unseen projects.

These splitters guarantee zero group leakage by holding out entire projects or scenarios.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple
from ml.dataset.schema import DiagnosticCase


class DataLeakageError(Exception):
    """Raised when group or target leakage is detected across train/test splits."""

    pass


class ProjectAwareSplitter:
    """Partitions diagnostic cases by project_id so no project appears in both train and test sets."""

    def __init__(self, test_projects: Set[str]):
        """Initialize with explicit set of project identifiers to hold out for testing."""
        if not test_projects:
            raise ValueError("test_projects set cannot be empty.")
        self.test_projects = set(test_projects)

    def split(self, cases: List[DiagnosticCase]) -> Tuple[List[DiagnosticCase], List[DiagnosticCase]]:
        """Partition cases into (train_cases, test_cases) with verified zero project overlap."""
        train_cases: List[DiagnosticCase] = []
        test_cases: List[DiagnosticCase] = []

        for case in cases:
            if case.project_id in self.test_projects:
                test_cases.append(case)
            else:
                train_cases.append(case)

        # Audit for leakage
        train_projects = {c.project_id for c in train_cases}
        test_projects = {c.project_id for c in test_cases}
        overlap = train_projects.intersection(test_projects)

        if overlap:
            raise DataLeakageError(
                f"Project leakage detected! The following projects appear in both train and test splits: {overlap}"
            )

        return train_cases, test_cases


class ScenarioAwareSplitter:
    """Partitions diagnostic cases by fault scenario_id so no scenario appears in both sets."""

    def __init__(self, test_scenarios: Set[str]):
        """Initialize with explicit set of scenario identifiers to hold out for testing."""
        if not test_scenarios:
            raise ValueError("test_scenarios set cannot be empty.")
        self.test_scenarios = set(test_scenarios)

    def split(self, cases: List[DiagnosticCase]) -> Tuple[List[DiagnosticCase], List[DiagnosticCase]]:
        """Partition cases into (train_cases, test_cases) with verified zero scenario overlap."""
        train_cases: List[DiagnosticCase] = []
        test_cases: List[DiagnosticCase] = []

        for case in cases:
            if case.scenario_id in self.test_scenarios:
                test_cases.append(case)
            else:
                train_cases.append(case)

        # Audit for leakage
        train_scenarios = {c.scenario_id for c in train_cases}
        test_scenarios = {c.scenario_id for c in test_cases}
        overlap = train_scenarios.intersection(test_scenarios)

        if overlap:
            raise DataLeakageError(
                f"Scenario leakage detected! The following scenarios appear in both splits: {overlap}"
            )

        return train_cases, test_cases


def group_cases_by_project(cases: List[DiagnosticCase]) -> Dict[str, List[DiagnosticCase]]:
    """Group a list of diagnostic cases by their project identifier."""
    grouped = defaultdict(list)
    for case in cases:
        grouped[case.project_id].append(case)
    return dict(grouped)


def group_cases_by_scenario(cases: List[DiagnosticCase]) -> Dict[str, List[DiagnosticCase]]:
    """Group a list of diagnostic cases by their scenario identifier."""
    grouped = defaultdict(list)
    for case in cases:
        grouped[case.scenario_id].append(case)
    return dict(grouped)
