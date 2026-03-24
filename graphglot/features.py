"""Feature definitions and typed constants for GraphGlot.

This is a **leaf module** with zero internal dependencies (only stdlib).
Every other module in the project can safely import from here without
circular-import issues.

Provides:
- ``Feature`` dataclass, ``FeatureKind`` / ``FeatureStatus`` enums
- One importable constant per GQL / Cypher / GraphGlot feature (~239 total)
- ``CATEGORY_MAP`` for human-readable feature categorisation
"""

from __future__ import annotations

import sys as _sys

from dataclasses import dataclass
from enum import StrEnum

# ── Core types ───────────────────────────────────────────────────────────────


class FeatureKind(StrEnum):
    EXTENSION = "extension"
    OPTIONAL = "optional"


class FeatureStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, eq=False)
class Feature:
    """GQL Feature — extension or optional."""

    id: str
    description: str
    kind: FeatureKind
    status: FeatureStatus = FeatureStatus.ACTIVE

    def __eq__(self, other):
        if isinstance(other, Feature):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return NotImplemented

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.id

    @property
    def is_extension(self) -> bool:
        return self.kind == FeatureKind.EXTENSION

    def category(self) -> str:
        if self.id.startswith("GG:"):
            return "GraphGlot extension"
        if self.id.startswith("CY:"):
            # CY:CL01 → key "CY:CL"
            key = self.id[:5]
            return CATEGORY_MAP.get(key, "Cypher extension")
        prefix = self.id[:2] if len(self.id) >= 2 and self.id[1].isalpha() else self.id[0]
        pattern = prefix + "#" * (4 - len(prefix))
        return CATEGORY_MAP.get(pattern, "Unknown")


CATEGORY_MAP: dict[str, str] = {
    "G###": "Graph pattern matching",
    "GA##": "Advanced",
    "GB##": "Basic syntax",
    "GC##": "Catalog management",
    "GD##": "Data Manipulation",
    "GE##": "Expressions",
    "GF##": "Functions",
    "GG##": "Graph types",
    "GH##": "Miscellaneous",
    "GL##": "Literals",
    "GP##": "Procedures",
    "GQ##": "Query composition",
    "GS##": "Session",
    "GT##": "Transactions",
    "GV##": "Value types",
    # Cypher extension categories
    "CY:CL": "Cypher clauses",
    "CY:EX": "Cypher expressions",
    "CY:OP": "Cypher operators",
    "CY:SQ": "Cypher subqueries",
    "CY:FN": "Cypher functions",
    "CY:QP": "Cypher query prefixes",
    "CY:DD": "Cypher DDL",
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _ext(id: str, desc: str) -> Feature:
    return Feature(id, desc, FeatureKind.EXTENSION)


def _opt(id: str, desc: str, status: FeatureStatus = FeatureStatus.ACTIVE) -> Feature:
    return Feature(id, desc, FeatureKind.OPTIONAL, status)


def _cy(id: str, desc: str) -> Feature:
    return Feature(id, desc, FeatureKind.EXTENSION)


# ── GraphGlot extensions (GG:) ──────────────────────────────────────────────

GG_SM01 = _ext("GG:SM01", "Session management: SESSION SET command")
GG_SM02 = _ext("GG:SM02", "Session management: SESSION RESET command")
GG_SM03 = _ext("GG:SM03", "Session management: SESSION CLOSE command")
GG_GE01 = _ext("GG:GE01", "Graph expressions: CURRENT_GRAPH and CURRENT_PROPERTY_GRAPH")
GG_SC01 = _ext("GG:SC01", "Schema references: AT clause")
GG_SC02 = _ext("GG:SC02", "Schema references: HOME_SCHEMA")
GG_SC03 = _ext("GG:SC03", "Schema references: CURRENT_SCHEMA")
GG_SS01 = _ext("GG:SS01", "SELECT statement")
GG_TL01 = _ext("GG:TL01", "Temporal literals")
GG_TF01 = _ext("GG:TF01", "Parameterless temporal functions (CURRENT_DATE, CURRENT_TIMESTAMP)")
GG_UE01 = _ext("GG:UE01", "Undirected full edge patterns (~[r]~, <~[r]~, ~[r]~>)")
GG_UE02 = _ext("GG:UE02", "Undirected abbreviated edge patterns (~, <~, ~>)")
GG_FN01 = _ext("GG:FN01", "Anonymous and dotted-namespace function calls")

# ── GQL Optional features (G###, GA##-GV##) ──────────────────────────────────

G002 = _opt("G002", "Different-edges match mode")
G003 = _opt("G003", "Explicit REPEATABLE ELEMENTS keyword")
G004 = _opt("G004", "Path variables")
G005 = _opt("G005", "Path search prefix in a path pattern")
G006 = _opt("G006", "Graph pattern KEEP clause: path mode prefix")
G007 = _opt("G007", "Graph pattern KEEP clause: path search prefix")
G010 = _opt("G010", "Explicit WALK keyword")
G011 = _opt("G011", "Advanced path modes: TRAIL")
G012 = _opt("G012", "Advanced path modes: SIMPLE")
G013 = _opt("G013", "Advanced path modes: ACYCLIC")
G014 = _opt("G014", "Explicit PATH/PATHS keywords")
G015 = _opt("G015", "All path search: explicit ALL keyword")
G016 = _opt("G016", "Any path search")
G017 = _opt("G017", "All shortest path search")
G018 = _opt("G018", "Any shortest path search")
G019 = _opt("G019", "Counted shortest path search")
G020 = _opt("G020", "Counted shortest group search")
G030 = _opt("G030", "Path multiset alternation")
G031 = _opt("G031", "Path multiset alternation: variable length path operands")
G032 = _opt("G032", "Path pattern union")
G033 = _opt("G033", "Path pattern union: variable length path operands")
G035 = _opt("G035", "Quantified paths")
G036 = _opt("G036", "Quantified edges")
G037 = _opt("G037", "Questioned paths")
G038 = _opt("G038", "Parenthesized path pattern expression")
G039 = _opt("G039", "Simplified path pattern expression: full defaulting")
G041 = _opt("G041", "Non-local element pattern predicates")
G043 = _opt("G043", "Complete full edge patterns")
G044 = _opt("G044", "Basic abbreviated edge patterns")
G045 = _opt("G045", "Complete abbreviated edge patterns")
G046 = _opt("G046", "Relaxed topological consistency: adjacent vertex patterns")
G047 = _opt("G047", "Relaxed topological consistency: concise edge patterns")
G048 = _opt("G048", "Parenthesized path pattern: subpath variable declaration")
G049 = _opt("G049", "Parenthesized path pattern: path mode prefix")
G050 = _opt("G050", "Parenthesized path pattern: WHERE clause")
G051 = _opt("G051", "Parenthesized path pattern: non-local predicates")
G060 = _opt("G060", "Bounded graph pattern quantifiers")
G061 = _opt("G061", "Unbounded graph pattern quantifiers")
G074 = _opt("G074", "Label expression: wildcard label")
G080 = _opt("G080", "Simplified path pattern expression: basic defaulting")
G081 = _opt("G081", "Simplified path pattern expression: full overrides")
G082 = _opt("G082", "Simplified path pattern expression: basic overrides")
G100 = _opt("G100", "ELEMENT_ID function")
G110 = _opt("G110", "IS DIRECTED predicate")
G111 = _opt("G111", "IS LABELED predicate")
G112 = _opt("G112", "IS SOURCE and IS DESTINATION predicate")
G113 = _opt("G113", "ALL_DIFFERENT predicate")
G114 = _opt("G114", "SAME predicate")
G115 = _opt("G115", "PROPERTY_EXISTS predicate")
GA01 = _opt("GA01", "IEEE 754 floating point operations", FeatureStatus.INACTIVE)
GA03 = _opt("GA03", "Explicit ordering of nulls")
GA04 = _opt("GA04", "Universal comparison")
GA05 = _opt("GA05", "Cast specification")
GA06 = _opt("GA06", "Value type predicate")
GA07 = _opt("GA07", "Ordering by discarded binding variables")
GA08 = _opt("GA08", "GQL-status objects with diagnostic records", FeatureStatus.INACTIVE)
GA09 = _opt("GA09", "Comparison of paths")
GB01 = _opt("GB01", "Long identifiers")
GB02 = _opt("GB02", "Double minus sign comments")
GB03 = _opt("GB03", "Double solidus comments")
GC01 = _opt("GC01", "Graph schema management")
GC02 = _opt("GC02", "Graph schema management: IF [ NOT ] EXISTS")
GC03 = _opt("GC03", "Graph type: IF [ NOT ] EXISTS")
GC04 = _opt("GC04", "Graph management")
GC05 = _opt("GC05", "Graph management: IF [ NOT ] EXISTS")
GD01 = _opt("GD01", "Updatable graphs")
GD02 = _opt("GD02", "Graph label set changes")
GD03 = _opt("GD03", "DELETE statement: subquery support")
GD04 = _opt("GD04", "DELETE statement: simple expression support")
GE01 = _opt("GE01", "Graph reference value expressions")
GE02 = _opt("GE02", "Binding table reference value expressions")
GE03 = _opt("GE03", "Let-binding of variables in expressions")
GE04 = _opt("GE04", "Graph parameters")
GE05 = _opt("GE05", "Binding table parameters")
GE06 = _opt("GE06", "Path value construction")
GE07 = _opt("GE07", "Boolean XOR")
GE08 = _opt("GE08", "Reference parameters")
GE09 = _opt("GE09", "Horizontal aggregation")
GF01 = _opt("GF01", "Enhanced numeric functions")
GF02 = _opt("GF02", "Trigonometric functions")
GF03 = _opt("GF03", "Logarithmic functions")
GF04 = _opt("GF04", "Enhanced path functions")
GF05 = _opt("GF05", "Multi-character TRIM function")
GF06 = _opt("GF06", "Explicit TRIM function")
GF07 = _opt("GF07", "Byte string TRIM function")
GF10 = _opt("GF10", "Advanced aggregate functions: general set functions")
GF11 = _opt("GF11", "Advanced aggregate functions: binary set functions")
GF12 = _opt("GF12", "CARDINALITY function")
GF13 = _opt("GF13", "SIZE function")
GF20 = _opt("GF20", "Aggregate functions in sort keys")
GG01 = _opt("GG01", "Graph with an open graph type")
GG02 = _opt("GG02", "Graph with a closed graph type")
GG03 = _opt("GG03", "Graph type inline specification")
GG04 = _opt("GG04", "Graph type like a graph")
GG05 = _opt("GG05", "Graph from a graph source")
GG20 = _opt("GG20", "Explicit element type names")
GG21 = _opt("GG21", "Explicit element type key label sets")
GG22 = _opt("GG22", "Element type key label set inference")
GG23 = _opt("GG23", "Optional element type key label sets")
GG24 = _opt("GG24", "Relaxed structural consistency", FeatureStatus.INACTIVE)
GG25 = _opt("GG25", "Relaxed key label set uniqueness for edge types", FeatureStatus.INACTIVE)
GG26 = _opt("GG26", "Relaxed property value type consistency", FeatureStatus.INACTIVE)
GH01 = _opt("GH01", "External object references")
GH02 = _opt("GH02", "Undirected edge patterns")
GL01 = _opt("GL01", "Hexadecimal literals")
GL02 = _opt("GL02", "Octal literals")
GL03 = _opt("GL03", "Binary literals")
GL04 = _opt("GL04", "Exact number in common notation without suffix")
GL05 = _opt("GL05", "Exact number in common notation or as decimal integer with suffix")
GL06 = _opt("GL06", "Exact number in scientific notation with suffix")
GL07 = _opt("GL07", "Approximate number in common notation or as decimal integer with suffix")
GL08 = _opt("GL08", "Approximate number in scientific notation with suffix")
GL09 = _opt("GL09", "Optional float number suffix")
GL10 = _opt("GL10", "Optional double number suffix")
GL11 = _opt("GL11", "Opt-out character escaping")
GL12 = _opt("GL12", "SQL datetime and interval formats")
GP01 = _opt("GP01", "Inline procedure")
GP02 = _opt("GP02", "Inline procedure with implicit nested variable scope")
GP03 = _opt("GP03", "Inline procedure with explicit nested variable scope")
GP04 = _opt("GP04", "Named procedure calls")
GP05 = _opt("GP05", "Procedure-local value variable definitions")
GP06 = _opt(
    "GP06",
    "Procedure-local value variable definitions: value variables based on simple expressions",
)
GP07 = _opt(
    "GP07", "Procedure-local value variable definitions: value variable based on subqueries"
)
GP08 = _opt("GP08", "Procedure-local binding table variable definitions")
GP09 = _opt(
    "GP09",
    "Procedure-local binding table variable definitions: binding table variables based on simple expressions or references",  # noqa: E501
)
GP10 = _opt(
    "GP10",
    "Procedure-local binding table variable definitions: binding table variables based on subqueries",  # noqa: E501
)
GP11 = _opt("GP11", "Procedure-local graph variable definitions")
GP12 = _opt(
    "GP12",
    "Procedure-local graph variable definitions: graph variables based on simple expressions or references",  # noqa: E501
)
GP13 = _opt(
    "GP13", "Procedure-local graph variable definitions: graph variables based on subqueries"
)
GP14 = _opt("GP14", "Binding tables as procedure arguments")
GP15 = _opt("GP15", "Graphs as procedure arguments")
GP16 = _opt("GP16", "AT schema clause")
GP17 = _opt("GP17", "Binding variable definition block")
GP18 = _opt("GP18", "Catalog and data statement mixing")
GQ01 = _opt("GQ01", "USE graph clause")
GQ02 = _opt("GQ02", "Composite query: OTHERWISE")
GQ03 = _opt("GQ03", "Composite query: UNION")
GQ04 = _opt("GQ04", "Composite query: EXCEPT DISTINCT")
GQ05 = _opt("GQ05", "Composite query: EXCEPT ALL")
GQ06 = _opt("GQ06", "Composite query: INTERSECT DISTINCT")
GQ07 = _opt("GQ07", "Composite query: INTERSECT ALL")
GQ08 = _opt("GQ08", "FILTER statement")
GQ09 = _opt("GQ09", "LET statement")
GQ10 = _opt("GQ10", "FOR statement: list value support")
GQ11 = _opt("GQ11", "FOR statement: WITH ORDINALITY")
GQ12 = _opt("GQ12", "ORDER BY and page statement: OFFSET clause")
GQ13 = _opt("GQ13", "ORDER BY and page statement: LIMIT clause")
GQ14 = _opt("GQ14", "Complex expressions in sort keys")
GQ15 = _opt("GQ15", "GROUP BY clause")
GQ16 = _opt("GQ16", "Pre-projection aliases in sort keys")
GQ17 = _opt("GQ17", "Element-wise group variable operations")
GQ18 = _opt("GQ18", "Scalar subqueries")
GQ19 = _opt("GQ19", "Graph pattern YIELD clause")
GQ20 = _opt("GQ20", "Advanced linear composition with NEXT")
GQ21 = _opt("GQ21", "OPTIONAL: Multiple MATCH statements")
GQ22 = _opt("GQ22", "EXISTS predicate: multiple MATCH statements")
GQ23 = _opt("GQ23", "FOR statement: binding table support")
GQ24 = _opt("GQ24", "FOR statement: WITH OFFSET")
GS01 = _opt("GS01", "SESSION SET command: session-local graph parameters")
GS02 = _opt("GS02", "SESSION SET command: session-local binding table parameters")
GS03 = _opt("GS03", "SESSION SET command: session-local value parameters")
GS04 = _opt("GS04", "SESSION RESET command: reset all characteristics")
GS05 = _opt("GS05", "SESSION RESET command: reset session schema")
GS06 = _opt("GS06", "SESSION RESET command: reset session graph")
GS07 = _opt("GS07", "SESSION RESET command: reset time zone displacement")
GS08 = _opt("GS08", "SESSION RESET command: reset all session parameters")
GS10 = _opt(
    "GS10", "SESSION SET command: session-local binding table parameters based on subqueries"
)
GS11 = _opt("GS11", "SESSION SET command: session-local value parameters based on sub-queries")
GS12 = _opt(
    "GS12",
    "SESSION SET command: session-local graph parameters based on simple expressions or references",
)
GS13 = _opt(
    "GS13",
    "SESSION SET command: session-local binding table parameters based on simple expressions or references",  # noqa: E501
)
GS14 = _opt(
    "GS14", "SESSION SET command: session-local value parameters based on simple expressions"
)
GS15 = _opt("GS15", "SESSION SET command: set time zone displacement")
GS16 = _opt("GS16", "SESSION RESET command: reset individual session parameters")
GT01 = _opt("GT01", "Explicit transaction commands")
GT02 = _opt("GT02", "Specified transaction characteristics")
GT03 = _opt("GT03", "Use of multiple graphs in a transaction", FeatureStatus.INACTIVE)
GV01 = _opt("GV01", "8 bit unsigned integer numbers")
GV02 = _opt("GV02", "8 bit signed integer numbers")
GV03 = _opt("GV03", "16 bit unsigned integer numbers")
GV04 = _opt("GV04", "16 bit signed integer numbers")
GV05 = _opt("GV05", "Small unsigned integer numbers")
GV06 = _opt("GV06", "32 bit unsigned integer numbers")
GV07 = _opt("GV07", "32 bit signed integer numbers")
GV08 = _opt("GV08", "Regular unsigned integer numbers")
GV09 = _opt("GV09", "Specified integer number precision")
GV10 = _opt("GV10", "Big unsigned integer numbers")
GV11 = _opt("GV11", "64 bit unsigned integer numbers")
GV12 = _opt("GV12", "64 bit signed integer numbers")
GV13 = _opt("GV13", "128 bit unsigned integer numbers")
GV14 = _opt("GV14", "128 bit signed integer numbers")
GV15 = _opt("GV15", "256 bit unsigned integer numbers")
GV16 = _opt("GV16", "256 bit signed integer numbers")
GV17 = _opt("GV17", "Decimal numbers")
GV18 = _opt("GV18", "Small signed integer numbers")
GV19 = _opt("GV19", "Big signed integer numbers")
GV20 = _opt("GV20", "16 bit floating point numbers")
GV21 = _opt("GV21", "32 bit floating point numbers")
GV22 = _opt("GV22", "Specified floating point number precision")
GV23 = _opt("GV23", "Floating point type name synonyms")
GV24 = _opt("GV24", "64 bit floating point numbers")
GV25 = _opt("GV25", "128 bit floating point numbers")
GV26 = _opt("GV26", "256 bit floating point numbers")
GV30 = _opt("GV30", "Specified character string minimum length")
GV31 = _opt("GV31", "Specified character string maximum length")
GV32 = _opt("GV32", "Specified character string fixed length")
GV35 = _opt("GV35", "Byte string types")
GV36 = _opt("GV36", "Specified byte string minimum length")
GV37 = _opt("GV37", "Specified byte string maximum length")
GV38 = _opt("GV38", "Specified byte string fixed length")
GV39 = _opt("GV39", "Temporal types: date, local datetime and local time support")
GV40 = _opt("GV40", "Temporal types: zoned datetime and zoned time support")
GV41 = _opt("GV41", "Temporal types: duration support")
GV45 = _opt("GV45", "Record types")
GV46 = _opt("GV46", "Closed record types")
GV47 = _opt("GV47", "Open record types")
GV48 = _opt("GV48", "Nested record types")
GV50 = _opt("GV50", "List value types")
GV55 = _opt("GV55", "Path value types")
GV60 = _opt("GV60", "Graph reference value types")
GV61 = _opt("GV61", "Binding table reference value types")
GV65 = _opt("GV65", "Dynamic union types")
GV66 = _opt("GV66", "Open dynamic union types")
GV67 = _opt("GV67", "Closed dynamic union types")
GV68 = _opt("GV68", "Dynamic property value types")
GV70 = _opt("GV70", "Immaterial value types")
GV71 = _opt("GV71", "Immaterial value types: null type support")
GV72 = _opt("GV72", "Immaterial value types: empty type support")
GV90 = _opt("GV90", "Explicit value type nullability")

# ── Cypher extensions (CY:) ─────────────────────────────────────────────────

CY_CL01 = _cy("CY:CL01", "MERGE clause")
CY_CL02 = _cy("CY:CL02", "UNWIND clause (maps to GQL FOR)")
CY_CL04 = _cy("CY:CL04", "CREATE clause (Cypher data-modifying)")
CY_CL05 = _cy("CY:CL05", "WITH clause (variable projection)")
CY_EX01 = _cy("CY:EX01", "List comprehension")
CY_EX02 = _cy("CY:EX02", "Pattern expression predicates")
CY_OP01 = _cy("CY:OP01", "String match predicates (STARTS WITH, ENDS WITH, CONTAINS)")
CY_OP02 = _cy("CY:OP02", "IN predicate (expr IN list)")
CY_OP03 = _cy("CY:OP03", "Regex match operator (=~)")
CY_OP04 = _cy("CY:OP04", "Subscript operator (expr[idx])")
CY_FN01 = _cy("CY:FN01", "List predicate functions (all/any/none/single)")
CY_FN04 = _cy("CY:FN04", "Cypher reduce() accumulator function")
CY_QP01 = _cy("CY:QP01", "EXPLAIN / PROFILE query prefix")
CY_TF01 = _cy("CY:TF01", "Temporal constructor/method functions")
CY_TF02 = _cy("CY:TF02", "No-argument duration() constructor")
CY_DD01 = _cy("CY:DD01", "CREATE / DROP INDEX")
CY_DD02 = _cy("CY:DD02", "CREATE / DROP CONSTRAINT")


# ── Registry & computed sets ─────────────────────────────────────────────────

ALL_FEATURE_MAP: dict[str, Feature] = {
    v.id: v for v in vars(_sys.modules[__name__]).values() if isinstance(v, Feature)
}

GQL_FEATURES = ALL_FEATURE_MAP  # backward-compat alias


def get_feature(feature_id: str) -> Feature:
    """Look up a Feature by its ID. Raises ValueError if not found."""
    feature = ALL_FEATURE_MAP.get(feature_id)
    if feature is not None:
        return feature
    raise ValueError(f"Unknown feature ID: {feature_id}")


def _is_gql(f: Feature) -> bool:
    return not f.id.startswith("CY:")


ALL_EXTENSION_FEATURES: set[Feature] = {
    f for f in ALL_FEATURE_MAP.values() if f.is_extension and _is_gql(f)
}
ALL_OPTIONAL_FEATURES: set[Feature] = {
    f for f in ALL_FEATURE_MAP.values() if not f.is_extension and _is_gql(f)
}
ALL_FEATURES: set[Feature] = {f for f in ALL_FEATURE_MAP.values() if _is_gql(f)}
