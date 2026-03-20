from __future__ import annotations

import typing as t

import graphglot.ast.functions as f

from graphglot import ast, features as F
from graphglot.dialect.cypher import CypherDialect
from graphglot.dialect.cypher_features import ALL_CYPHER_FEATURES
from graphglot.features import ALL_EXTENSION_FEATURES, Feature
from graphglot.generator import func_generators
from graphglot.generator.generators.patterns import generate_quantified_path_primary
from graphglot.lexer import TokenType
from graphglot.parser import Parser as BaseParser
from graphglot.transformations import with_to_next

# ==============================================================================
# Unsupported Mandatory GQL Features not supported by Neo4j:
# https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/unsupported-mandatory/
#
# Supported Mandatory GQL Features:
# https://neo4j.com/docs/cypher-manual/25/appendix/gql-conformance/supported-mandatory/
#
# Supported Optional GQL Features:
# https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/supported-optional/
# https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/analogous-cypher/
#
# Additional Cypher-specific features:
# https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/additional-cypher/
# ==============================================================================

# Extension features listed here are UNSUPPORTED by Neo4j.  Because extension
# features are enabled by default (ALL_EXTENSION_FEATURES), excluding them here
# effectively narrows core or optional GQL features that Neo4j only partially
# covers.  For example, G043 (complete full edge patterns) is listed in
# _NEO4J_SUPPORTED_OPTIONAL, but only the directed form (<-[r]->) works —
# GG:UE01 gates the 3 tilde/undirected forms, so marking it unsupported here
# blocks them while the directed form still passes validation.
# See ADR-003 for the rationale behind this pattern.
_NEO4J_UNSUPPORTED_EXT: set[Feature] = {
    F.GG_SM01,
    F.GG_SM02,
    F.GG_SM03,
    F.GG_GE01,
    F.GG_SC01,
    F.GG_SC02,
    F.GG_SC03,
    F.GG_SS01,
    F.GG_TF01,
    F.GG_TL01,
    # Neo4j only has directed edges; undirected tilde forms are unsupported.
    F.GG_UE01,
    F.GG_UE02,
}

_NEO4J_SUPPORTED_OPTIONAL: set[Feature] = {
    F.G002,
    F.G003,
    F.G004,
    F.G005,
    F.G016,
    F.G017,
    F.G018,
    F.G019,
    F.G020,
    F.G035,
    F.G036,
    # G043: Complete full edge patterns. Neo4j supports <-[r]-> (LeftOrRight) but
    # not the 3 tilde/undirected forms (~[r]~, <~[r]~, ~[r]~>), which are gated
    # by GG:UE01 in _NEO4J_UNSUPPORTED_EXT.
    F.G043,
    # G044: Cypher uses abbreviated edge patterns (-->, <--, --, ->, <-, -)
    F.G044,
    # G045: Complete abbreviated edge patterns. Neo4j supports <-> (Cypher <-->)
    # but not the 3 tilde/undirected forms (~, <~, ~>), which are gated
    # by GG:UE02 in _NEO4J_UNSUPPORTED_EXT.
    F.G045,
    # G047 removed: Neo4j rejects edges without adjacent node patterns
    # (e.g. (a)-->-->(b)). Our earlier test used a normal chain which was wrong.
    F.G050,
    F.G051,
    F.G060,
    F.G061,
    F.G074,
    # GQL's ELEMENT_ID() function is equivalent to Cypher's elementId() function
    F.G100,
    # G111: label predicate in WHERE (n:Label) — Cypher colon syntax
    F.G111,
    # GA05: Neo4j supports type conversion via toBoolean/toInteger/toFloat/toString
    # which are semantically equivalent to GQL's CAST(x AS TYPE)
    # GE07: XOR boolean operator — Neo4j supports Cypher's XOR
    F.GE07,
    F.GA05,
    F.GA06,
    F.GA07,
    F.GB01,
    # GB03: Cypher uses // comments
    F.GB03,
    F.GD01,
    F.GD02,
    # GD04: DELETE with simple expression (subscript/property access)
    F.GD04,
    # Note the following exceptions: GQL supports CEILING() as a synonym for the CEIL() function.
    # Cypher only supports ceil().
    F.GF01,
    F.GF02,
    F.GF03,
    # GQL's PATH_LENGTH() function is equivalent to Cypher's length() function.
    F.GF04,
    F.GF05,
    # In GQL, TRIM() removes only space characters. In Cypher, trim() removes any whitespace
    # character.
    F.GF06,
    # GQL's COLLECT_LIST() function is equivalent to Cypher's collect() function.
    # GQL's STDEV_SAMP() function is equivalent to Cypher's stDev() function.
    # GQL's STDEV_POP() function is equivalent to Cypher's stDevP() function.
    F.GF10,
    # GQL's PERCENTILE_CONT() function is equivalent to Cypher's percentileCont() function.
    # GQL's PERCENTILE_DISC() function is equivalent to Cypher's percentileDisc() function.
    F.GF11,
    # GF20: Aggregate functions in sort keys (ORDER BY max(...))
    F.GF20,
    F.GG01,
    # Hex integer literals (e.g. 0xFF)
    F.GL01,
    # Octal integer literals (e.g. 0o77)
    F.GL02,
    # Decimal literals without suffix (e.g. 3.14, 0.5)
    F.GL04,
    F.GP01,
    F.GP02,
    F.GP03,
    F.GP04,
    # Cypher's USE clause supports static graph references (e.g. USE myComposite.myGraph)and dynamic
    # graph references (e.g. USE graph.byName(<expression>)). However, Cypher does not support GQL's
    # full graph reference syntax. For example, GQL's graph reference values CURRENT_GRAPH and
    # CURRENT_PROPERTY_GRAPH cannot be used in Cypher.
    F.GQ01,
    F.GQ03,
    F.GQ08,
    F.GQ09,
    # GQ10: UNWIND is Cypher's equivalent of GQL's FOR statement
    F.GQ10,
    # Cypher requires using the WITH clause, which GQL does not.
    F.GQ12,
    F.GQ13,
    F.GQ14,  # Not in docs, but seems to be supported by Neo4j
    F.GQ16,  # Not in docs, but seems to be supported by Neo4j
    # The GQL standard includes a YIELD clause for its NEXT statement which Cypher does not
    # implement.
    F.GQ20,
    F.GQ22,
    F.GV39,
    F.GV40,
    # Cypher supports duration types (e.g. duration('P1Y2M3D'))
    F.GV41,
    # GQL's open RECORD type is equivalent to the MAP type in Cypher.
    F.GV45,
    # Nested record types (maps containing maps)
    F.GV48,
    F.GV50,
    F.GV55,
    F.GV66,
    F.GV67,
    F.GV70,
    F.GV71,
}


# AST fragment representing the literal `1` wrapped as a NumericValueExpression.
_ONE = ast.NumericValueExpression(
    base=ast.Term(
        base=ast.Factor(
            sign=ast.Sign.PLUS_SIGN,
            numeric_primary=ast.UnsignedNumericLiteral(value=1),
        )
    )
)


def _parse_exponential_function(parser: BaseParser) -> ast.ExponentialFunction:
    """Parse `EXP(x)` (GQL) or `e()` (Cypher) as ExponentialFunction.

    Cypher's `e()` is equivalent to GQL's `EXP(1)`.
    """
    if parser._match(TokenType.E):
        (_, _, _) = parser.seq(TokenType.E, TokenType.LEFT_PAREN, TokenType.RIGHT_PAREN)
        return ast.ExponentialFunction(numeric_value_expression=_ONE.deep_copy())

    (_, _, numeric_value_expression, _) = parser.seq(
        TokenType.EXP,
        TokenType.LEFT_PAREN,
        parser.get_parser(ast.NumericValueExpression),
        TokenType.RIGHT_PAREN,
    )
    return ast.ExponentialFunction(numeric_value_expression=numeric_value_expression)


_NEO4J_EXTRA_FUNCTIONS: dict[str, type[f.Func]] = {
    "RANDOMUUID": f.RandomUUID,
    "TIMESTAMP": f.TimestampFunc,
    "VALUETYPE": f.ValueTypeFunc,
    "ELEMENTID": f.ElementId,
    "TOSTRINGORNULL": f.ToStringOrNull,
    "TOBOOLEANORNULL": f.ToBooleanOrNull,
    "TOINTEGERORNULL": f.ToIntegerOrNull,
    "TOFLOATORNULL": f.ToFloatOrNull,
    "TOBOOLEANLIST": f.ToBooleanList,
    "TOINTEGERLIST": f.ToIntegerList,
    "TOFLOATLIST": f.ToFloatList,
    "TOSTRINGLIST": f.ToStringList,
    "POINT": f.PointConstructor,
    "POINT.DISTANCE": f.PointDistance,
    "POINT.WITHINBBOX": f.PointWithinBBox,
}


class Neo4j(CypherDialect):
    """Neo4j Cypher dialect (Neo4j 2026+ community edition)."""

    SUPPORTED_FEATURES: t.ClassVar[set[Feature]] = (
        (ALL_EXTENSION_FEATURES - _NEO4J_UNSUPPORTED_EXT)
        | _NEO4J_SUPPORTED_OPTIONAL
        | ALL_CYPHER_FEATURES
    )

    TRANSFORMATIONS: t.ClassVar[list] = [with_to_next, *CypherDialect.TRANSFORMATIONS]

    KEYWORD_OVERRIDES: t.ClassVar[dict[str, str]] = {
        **CypherDialect.KEYWORD_OVERRIDES,
        "STDDEV_SAMP": "STDEV",
        "STDDEV_POP": "STDEVP",
        "ELEMENT_ID": "ELEMENTID",
        "PATH_LENGTH": "LENGTH",
        "PERCENTILE_CONT": "PERCENTILECONT",
        "PERCENTILE_DISC": "PERCENTILEDISC",
    }

    class Lexer(CypherDialect.Lexer):
        KEYWORDS: t.ClassVar[dict[str, t.Any]] = {**CypherDialect.Lexer.KEYWORDS}

        # ----------------------------------------------------------------------
        # Analogous Cypher features
        # https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/analogous-cypher/
        # ----------------------------------------------------------------------

        # GQL's open RECORD type is equivalent to the MAP type in Cypher.
        # GQL's ELEMENT_ID() function is equivalent to Cypher's elementId() function
        KEYWORDS.pop("ELEMENT_ID")
        KEYWORDS["ELEMENTID"] = TokenType.ELEMENT_ID

        # GQL's PATH_LENGTH() function is equivalent to Cypher's length() function.
        KEYWORDS.pop("PATH_LENGTH")
        KEYWORDS["LENGTH"] = TokenType.PATH_LENGTH

        # GQL's STDEV_SAMP() function is equivalent to Cypher's stDev() function.
        # GQL's STDEV_POP() function is equivalent to Cypher's stDevP() function.
        KEYWORDS.pop("STDDEV_SAMP")
        KEYWORDS.pop("STDDEV_POP")
        KEYWORDS["STDEV"] = TokenType.STDDEV_SAMP
        KEYWORDS["STDEVP"] = TokenType.STDDEV_POP

        # GQL's PERCENTILE_CONT() function is equivalent to Cypher's percentileCont() function.
        # GQL's PERCENTILE_DISC() function is equivalent to Cypher's percentileDisc() function.
        KEYWORDS.pop("PERCENTILE_CONT")
        KEYWORDS.pop("PERCENTILE_DISC")
        KEYWORDS["PERCENTILECONT"] = TokenType.PERCENTILE_CONT
        KEYWORDS["PERCENTILEDISC"] = TokenType.PERCENTILE_DISC

        # ----------------------------------------------------------------------
        # Supported Optional GQL Features
        # https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/supported-optional/
        # ----------------------------------------------------------------------

        # GQL supports CEILING() as a synonym for the CEIL() function. Cypher only supports CEIL().
        KEYWORDS.pop("CEILING")

        # Cypher uses the log() function instead of GQL's LN() function.
        # The general LOG() function as defined in GQL is not supported by Cypher.
        KEYWORDS.pop("LN")
        KEYWORDS.pop("LOG")
        KEYWORDS["LOG"] = TokenType.LN

        # Cypher uses the exponentiation operator (^) instead of GQL's POWER() function.
        KEYWORDS.pop("POWER")

        # GQL also defines a parameterless version of the function not in Cypher: CURRENT_TIME
        KEYWORDS.pop("CURRENT_TIME")

        # ----------------------------------------------------------------------

        # GQL's MOD() function is not supported by Cypher. Cypher uses % instead.
        KEYWORDS.pop("MOD")

        # Cypher's e() is equivalent to GQL's EXP(1) function
        KEYWORDS["E"] = TokenType.E

    class Parser(CypherDialect.Parser):
        FUNCTIONS: t.ClassVar[dict[str, type[f.Func]]] = {
            **CypherDialect.Parser.FUNCTIONS,
            **_NEO4J_EXTRA_FUNCTIONS,
        }

        PARSERS: t.ClassVar[dict[t.Any, t.Any]] = {
            **CypherDialect.Parser.PARSERS,
            ast.ExponentialFunction: _parse_exponential_function,
        }

    class Generator(CypherDialect.Generator):
        GENERATORS: t.ClassVar[dict[t.Any, t.Any]] = {
            **CypherDialect.Generator.GENERATORS,
            **func_generators(_NEO4J_EXTRA_FUNCTIONS),
            # Use standard GQL quantifier syntax {N,M} instead of Cypher *N..M
            ast.QuantifiedPathPrimary: generate_quantified_path_primary,
        }
