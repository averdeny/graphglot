"""Loader for openCypher TCK .feature files using gherkin-official."""

from __future__ import annotations

import re

from pathlib import Path

from gherkin.parser import Parser
from gherkin.pickles.compiler import Compiler

from tests.graphglot.tck.models import ExpectedOutcome, FeatureFile, TckScenario

# Regex for error outcome steps
_ERROR_RE = re.compile(r"^a (\w+) should be raised at (compile time|runtime|any time):\s*(.+)$")

# Regex for extracting scenario number from name like "[7] Some name"
_SCENARIO_NUM_RE = re.compile(r"^\[(\d+)\]\s*(.*)$")

# Vendored from https://github.com/opencypher/openCypher (commit ecbde675)
TCK_FEATURES_DIR = Path(__file__).resolve().parent / "features"


def _detect_outcome(steps: list[dict]) -> tuple[ExpectedOutcome, str | None, str | None]:
    """Detect expected outcome from pickle steps.

    Returns (outcome, error_type, error_detail).
    """
    for step in steps:
        if step.get("type") != "Outcome":
            continue
        text = step["text"]

        m = _ERROR_RE.match(text)
        if m:
            error_class, when, detail = m.groups()
            error_type = error_class
            error_detail = detail.strip()

            if when == "compile time":
                return ExpectedOutcome.ERROR_COMPILE, error_type, error_detail
            elif when == "runtime":
                return ExpectedOutcome.ERROR_RUNTIME, error_type, error_detail
            else:  # "any time"
                return ExpectedOutcome.ERROR_ANYTIME, error_type, error_detail

        if "the result should be empty" in text:
            return ExpectedOutcome.RESULT_EMPTY, None, None
        if "the result should be" in text:
            return ExpectedOutcome.RESULT, None, None

    # Default: positive result (e.g., only "no side effects" step)
    return ExpectedOutcome.RESULT, None, None


def _extract_queries(steps: list[dict], step_type: str) -> list[str]:
    """Extract query strings from pickle steps of a given type."""
    queries = []
    for step in steps:
        if step.get("type") != step_type:
            continue
        arg = step.get("argument")
        if arg and "docString" in arg:
            content = arg["docString"]["content"].strip()
            if content:
                queries.append(content)
    return queries


def _parse_scenario_name(name: str) -> tuple[int, str]:
    """Parse scenario name into (number, clean_name).

    "[7] Fail when ..." → (7, "Fail when ...")
    "Some name" → (0, "Some name")
    """
    m = _SCENARIO_NUM_RE.match(name)
    if m:
        return int(m.group(1)), m.group(2)
    return 0, name


def load_feature_file(path: str | Path) -> FeatureFile:
    """Load a single .feature file and return a FeatureFile with expanded scenarios."""
    path = Path(path)
    parser = Parser()
    compiler = Compiler()

    content = path.read_text(encoding="utf-8")
    doc = parser.parse(content)
    doc["uri"] = str(path)

    feature_name = doc["feature"]["name"]
    pickles = compiler.compile(doc)

    # Track outline row indices per scenario number
    outline_counters: dict[int, int] = {}

    scenarios = []
    for pickle in pickles:
        name = pickle["name"]
        scenario_number, clean_name = _parse_scenario_name(name)
        steps = pickle.get("steps", [])

        # Detect if this is an outline expansion (multiple astNodeIds)
        is_outline = len(pickle.get("astNodeIds", [])) > 1
        outline_row = None
        if is_outline:
            count = outline_counters.get(scenario_number, 0)
            outline_row = count
            outline_counters[scenario_number] = count + 1

        # Extract main query (Action steps)
        action_queries = _extract_queries(steps, "Action")
        query = action_queries[0] if action_queries else ""

        # Extract setup queries (Context steps with docStrings)
        setup_queries = _extract_queries(steps, "Context")

        # Detect outcome
        outcome, error_type, error_detail = _detect_outcome(steps)

        # Extract tags
        tags = tuple(t.get("name", "") for t in pickle.get("tags", []))

        scenario = TckScenario(
            feature_name=feature_name,
            scenario_name=clean_name,
            scenario_number=scenario_number,
            tags=tags,
            query=query,
            setup_queries=tuple(setup_queries),
            outcome=outcome,
            error_type=error_type,
            error_detail=error_detail,
            source_file=str(path),
            outline_row=outline_row,
        )
        scenarios.append(scenario)

    return FeatureFile(path=str(path), feature_name=feature_name, scenarios=scenarios)


def load_all_features(base_dir: str | Path | None = None) -> list[FeatureFile]:
    """Load all .feature files from the TCK features directory."""
    base = Path(base_dir) if base_dir else TCK_FEATURES_DIR
    feature_files = sorted(base.rglob("*.feature"))

    results = []
    for fp in feature_files:
        ff = load_feature_file(fp)
        if ff.scenarios:
            results.append(ff)

    return results


def load_all_scenarios(base_dir: str | Path | None = None) -> list[TckScenario]:
    """Load all scenarios from all .feature files."""
    features = load_all_features(base_dir)
    return [s for ff in features for s in ff.scenarios]
