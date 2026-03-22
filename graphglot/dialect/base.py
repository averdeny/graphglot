"""Base dialect interface for GraphGlot."""

from __future__ import annotations

import importlib
import sys
import typing as t

from dataclasses import dataclass, field
from enum import StrEnum

from graphglot.features import ALL_FEATURES, Feature, get_feature
from graphglot.generator import Generator as BaseGenerator
from graphglot.lexer import Lexer as BaseLexer, TokenType
from graphglot.parser import Parser as BaseParser
from graphglot.transformations import resolve_ambiguous
from graphglot.utils.helper import seq_get

if t.TYPE_CHECKING:
    from graphglot.analysis.models import AnalysisResult, SemanticDiagnostic
    from graphglot.ast.base import Expression
    from graphglot.error import Diagnostic
    from graphglot.lexer.lexer import Token
    from graphglot.lineage.models import LineageGraph
    from graphglot.transformations import Transformation


@dataclass
class ValidationResult:
    """Result of full pipeline validation."""

    success: bool
    stage: str  # "lexer", "parser", "analysis", or "ok"
    error: Exception | None = None
    features: set[Feature] = field(default_factory=set)
    diagnostics: list[SemanticDiagnostic] = field(default_factory=list)
    expressions: list[Expression] = field(default_factory=list)
    query: str = ""

    @property
    def all_diagnostics(self) -> list[Diagnostic]:
        """Unified diagnostics from all phases."""

        result: list[Diagnostic] = []
        if self.error is not None:
            if hasattr(self.error, "to_diagnostics"):
                result.extend(self.error.to_diagnostics())
            elif hasattr(self.error, "to_diagnostic"):
                result.append(self.error.to_diagnostic())
        for sd in self.diagnostics:
            result.append(sd.to_diagnostic())
        return result


UNESCAPED_SEQUENCES = {
    "\\a": "\a",
    "\\b": "\b",
    "\\f": "\f",
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
    "\\v": "\v",
    "\\\\": "\\",
}


class Dialects(StrEnum):
    """Dialects supported by GraphGlot."""

    IR = "ir"  # Internal representation

    FULLGQL = "fullgql"
    COREGQL = "coregql"
    NEO4J = "neo4j"
    # ETC


# The module names and the supported dialects must be in sync.
DIALECT_MODULE_NAMES = [dialect.value.lower() for dialect in Dialects]


class Version(int):
    """Version number for dialects."""

    def __new__(cls, version_str: str | None, *args, **kwargs):
        if version_str:
            parts = version_str.split(".")
            parts.extend(["0"] * (3 - len(parts)))
            v = int("".join([p.zfill(3) for p in parts]))
        else:
            # No version defined means we should support the latest engine semantics, so
            # the comparison to any specific version should yield that latest is greater
            v = sys.maxsize

        return super().__new__(cls, v)


class _Dialect(type):
    _classes: t.ClassVar[dict[str, type[Dialect]]] = {}

    def __eq__(cls, other: t.Any) -> bool:
        if cls is other:
            return True
        if isinstance(other, str):
            return cls is cls.get(other)
        if isinstance(other, Dialect):
            return cls is type(other)

        return False

    def __hash__(cls) -> int:
        return hash(cls.__name__.lower())

    @property
    def classes(cls):
        if len(DIALECT_MODULE_NAMES) != len(cls._classes):
            for key in DIALECT_MODULE_NAMES:
                cls._try_load(key)

        return cls._classes

    @classmethod
    def _try_load(cls, key: str | Dialects) -> None:
        if isinstance(key, Dialects):
            key = key.value

        # This import will lead to a new dialect being loaded, and hence, registered.
        # We check that the key is an actual graphglot module to avoid blindly importing
        # files. Custom user dialects need to be imported at the top-level package, in
        # order for them to be registered as soon as possible.
        if key in DIALECT_MODULE_NAMES:
            importlib.import_module(f"graphglot.dialect.{key}")

    @classmethod
    def __getitem__(cls, key: str) -> type[Dialect]:
        if key not in cls._classes:
            cls._try_load(key)

        return cls._classes[key]

    @classmethod
    def get(cls, key: str, default: type[Dialect] | None = None) -> type[Dialect] | None:
        if key not in cls._classes:
            cls._try_load(key)

        return cls._classes.get(key, default)

    def __new__(cls, clsname, bases, attrs):
        klass = super().__new__(cls, clsname, bases, attrs)
        enum = Dialects.__members__.get(clsname.upper())
        cls._classes[enum.value if enum is not None else clsname.lower()] = klass

        base = seq_get(bases, 0)
        base_lexer = (getattr(base, "lexer_class", BaseLexer),)
        base_parser = (getattr(base, "parser_class", BaseParser),)
        base_generator = (getattr(base, "generator_class", BaseGenerator),)

        # Dialect inheriting from the base class can define their dialect-specific
        # Lexer, Parser, and Generator classes. If they don't, use the corresponding
        # base classes.
        klass.lexer_class = klass.__dict__.get(
            "Lexer",
            type("Lexer", base_lexer, {}),
        )
        klass.parser_class = klass.__dict__.get(
            "Parser",
            type("Parser", base_parser, {}),
        )
        klass.generator_class = klass.__dict__.get(
            "Generator", type("Generator", base_generator, {})
        )

        if "\\" in klass.lexer_class.STRING_ESCAPES:
            klass.UNESCAPED_SEQUENCES = {
                **UNESCAPED_SEQUENCES,
                **klass.UNESCAPED_SEQUENCES,
            }

        return klass


class Dialect(metaclass=_Dialect):
    """Base class for all dialects in GraphGlot."""

    lexer_class: t.ClassVar[type[BaseLexer]]
    parser_class: t.ClassVar[type[BaseParser]]
    generator_class: t.ClassVar[type[BaseGenerator]]

    UNESCAPED_SEQUENCES: t.ClassVar[dict[str, str]] = {}
    """Mapping of an escaped sequence (`\\n`) to its unescaped version (`\n`).
    This is used in the lexer to unescape strings."""

    NUMBERS_CAN_BE_UNDERSCORE_SEPARATED = True
    """Whether numbers can be underscore separated and follow the rule:

    ```
    <digit> [ { [ <underscore> ] <digit> }... ]
    ```
    """

    SUPPORTED_FEATURES: t.ClassVar[set[Feature]] = ALL_FEATURES
    """GQL features supported by the dialect (core + optional)."""

    TRANSFORMATIONS: t.ClassVar[list[Transformation]] = [resolve_ambiguous]
    """Ordered list of AST transformations to apply when normalizing parsed trees."""

    NON_RESERVED_WORDS: t.ClassVar[set[TokenType]] = {
        TokenType.ACYCLIC,
        TokenType.BINDING,
        TokenType.BINDINGS,
        TokenType.CONNECTING,
        TokenType.DESTINATION,
        TokenType.DIFFERENT,
        TokenType.DIRECTED,
        TokenType.EDGE,
        TokenType.EDGES,
        TokenType.ELEMENT,
        TokenType.ELEMENTS,
        TokenType.FIRST,
        TokenType.GRAPH,
        TokenType.GROUPS,
        TokenType.KEEP,
        TokenType.LABEL,
        TokenType.LABELED,
        TokenType.LABELS,
        TokenType.LAST,
        TokenType.NFC,
        TokenType.NFD,
        TokenType.NFKC,
        TokenType.NFKD,
        TokenType.NO,
        TokenType.NODE,
        TokenType.NORMALIZED,
        TokenType.ONLY,
        TokenType.ORDINALITY,
        TokenType.PROPERTY,
        TokenType.READ,
        TokenType.RELATIONSHIP,
        TokenType.RELATIONSHIPS,
        TokenType.REPEATABLE,
        TokenType.SHORTEST,
        TokenType.SIMPLE,
        TokenType.SOURCE,
        # TokenType.TABLE — non-reserved per §21.3 but causes parse ambiguity
        # with BindingTableReferenceValueExpression (TABLE { ... })
        TokenType.TEMP,
        TokenType.TO,
        TokenType.TRAIL,
        TokenType.TRANSACTION,
        # TokenType.TYPE — non-reserved per §21.3 but causes parse ambiguity
        # with GRAPH TYPE / NODE TYPE / EDGE TYPE in DDL productions
        TokenType.UNDIRECTED,
        TokenType.VERTEX,
        TokenType.WALK,
        TokenType.WITHOUT,
        TokenType.WRITE,
        TokenType.ZONE,
    }
    """Set of non-reserved words that are used in the dialect."""

    def __init__(self, **kwargs: t.Any) -> None:
        self.version = Version(kwargs.pop("version", None))
        self.settings = kwargs

    def __eq__(self, other: t.Any) -> bool:
        if not isinstance(other, Dialect):
            return False
        return (
            type(self) is type(other)
            and self.version == other.version
            and self.settings == other.settings
        )

    def __hash__(self) -> int:
        return hash((type(self), self.version, tuple(sorted(self.settings.items()))))

    @classmethod
    def get_or_raise(cls, dialect: DialectType | None, **kwargs: t.Any) -> Dialect:
        """
        Look up a dialect in the global dialect registry and return it if it exists.

        Args:
            dialect: The target dialect.
            **kwargs: Additional keyword arguments to pass to the dialect constructor.

        Example:
            >>> dialect = Dialect.get_or_raise("neo4j")

        Returns:
            The corresponding Dialect instance.
        """

        if not dialect or dialect == "ir":
            return cls(**kwargs)
        if isinstance(dialect, Dialect):
            return dialect
        if isinstance(dialect, str):
            dialect_name = dialect.strip()
            result = cls.get(dialect_name)
            if not result:
                from difflib import get_close_matches

                close_matches = get_close_matches(dialect_name, list(DIALECT_MODULE_NAMES), n=1)

                similar = seq_get(close_matches, 0) or ""
                if similar:
                    similar = f" Did you mean {similar}?"

                raise ValueError(f"Unknown dialect '{dialect_name}'.{similar}")

            return result(**kwargs)

        if isinstance(dialect, type) and issubclass(dialect, Dialect):
            return dialect(**kwargs)

        raise TypeError(f"Invalid dialect specifier: {dialect!r}")

    def is_feature_supported(self, feature: Feature | str) -> bool:
        """Check if a feature is supported by the dialect."""
        if isinstance(feature, str):
            feature = get_feature(feature)
        return feature in self.SUPPORTED_FEATURES

    def lexer(self, **opts) -> BaseLexer:
        """Instantiate the lexer for the dialect."""
        return self.lexer_class(**{"dialect": self, **opts})

    def tokenize(self, query: str, **opts) -> list[Token]:
        """Tokenize a GQL query."""
        return self.lexer(**opts).tokenize(query)

    def parser(self, **opts) -> BaseParser:
        """Instantiate the parser for the dialect."""
        return self.parser_class(**{"dialect": self, **opts})

    def parse(self, query: str, **opts: t.Any) -> list[Expression]:
        """Parse a GQL query."""
        parsed = self.parser(**opts).parse(self.tokenize(query), query)
        return [expr for expr in parsed if expr is not None]

    def generator(self, **opts) -> BaseGenerator:
        """Instantiate the generator for the dialect."""
        return self.generator_class(**{"dialect": self, **opts})

    def generate(self, expression: Expression, copy: bool = False, **opts) -> str:
        """Generate a GQL string from an expression."""
        return self.generator(**opts).generate(expression, copy=copy)

    def transform(self, expressions: list[Expression]) -> list[Expression]:
        """Apply all dialect transformations to parsed expressions.

        Deep-copies the trees first, then applies each transformation in order.
        Returns the original trees unchanged if TRANSFORMATIONS is empty.
        """
        if not self.TRANSFORMATIONS:
            return expressions
        results = []
        for expr in expressions:
            result = expr.deep_copy()
            for fn in self.TRANSFORMATIONS:
                result = fn(result)
            results.append(result)
        return results

    def transpile(self, query: str, **opts: t.Any) -> list[str]:
        """Parse a query and re-generate it using this dialect.

        Equivalent to validate → transform → validate → generate for each
        statement.  For cross-dialect transpilation, use the top-level
        ``gg transpile`` CLI command.

        Raises:
            FeatureError: If the query or the transformed AST requires
                features not supported by this dialect.
            TokenError: If the query cannot be tokenized.
            ParseError: If the query cannot be parsed.
        """
        from graphglot.error import FeatureError

        # Validate input (lexer + parser + semantic analysis)
        result = self.validate(query, **opts)
        if not result.success:
            if result.error:
                raise result.error
            msgs = "; ".join(d.message for d in result.diagnostics)
            raise FeatureError(msgs)

        # Transform
        expressions = self.transform(result.expressions)

        # Validate output (AST features + semantic analysis)
        _validate_for_dialect(expressions, self)

        return [self.generate(expression, copy=False, **opts) for expression in expressions]

    def analyze(
        self,
        query: str,
        disabled_rules: set[str] | None = None,
        **opts: t.Any,
    ) -> list[AnalysisResult]:
        """Parse and semantically analyze a GQL query.

        Returns one :class:`AnalysisResult` per top-level statement.

        *disabled_rules* is forwarded to :meth:`SemanticAnalyzer.analyze`.
        """
        from graphglot.analysis import SemanticAnalyzer

        expressions = self.parse(query, **opts)
        expressions = self.transform(expressions)
        analyzer = SemanticAnalyzer()
        return [analyzer.analyze(expr, self, disabled_rules=disabled_rules) for expr in expressions]

    def lineage(self, query: str, **opts: t.Any) -> list[LineageGraph]:
        """Parse, transform, and extract data lineage from a query.

        Returns one :class:`LineageGraph` per top-level statement.

        Raises:
            UnsupportedLineageError: If a statement type is not supported
                for lineage analysis (e.g. SELECT, INSERT, DELETE).
        """
        from graphglot.lineage import LineageAnalyzer

        expressions = self.parse(query, **opts)
        expressions = self.transform(expressions)
        analyzer = LineageAnalyzer()
        results: list[LineageGraph] = []
        for expr in expressions:
            self._check_unsupported_lineage(expr)
            results.append(analyzer.analyze(expr, query_text=query))
        return results

    @staticmethod
    def _check_unsupported_lineage(expr: Expression) -> None:
        """Raise if the expression is unsupported for lineage analysis."""
        from graphglot import ast
        from graphglot.error import UnsupportedLineageError

        for node in expr.dfs():
            if isinstance(node, ast.SelectStatement):
                raise UnsupportedLineageError(
                    "SELECT statements are not yet supported by lineage analysis", node
                )

    def validate(
        self,
        query: str,
        disabled_rules: set[str] | None = None,
        **opts,
    ) -> ValidationResult:
        """Tokenize, parse, and semantically analyze a query.

        Returns a :class:`ValidationResult` with:
        - success/failure status and the stage that failed
        - the error if any stage failed
        - the set of GQL features required by the query (on success)
        - semantic diagnostics (on analysis failure)

        **Operand type checking** uses two layers that run at different stages:

        1. *Plausibility* (transform stage, ``typing/rules/resolution.py``):
           each ambiguous expression has an allowlist of type kinds that can
           participate at all.  If any operand is concretely outside the
           allowlist (e.g. STRING in arithmetic, NODE in concat) the resolver
           bails to ``unknown()`` so the node is **not** transformed into a
           concrete GQL type.

        2. *Compatibility* (analysis stage, ``type-mismatch`` structural rule):
           catches operands that are individually plausible but incompatible
           *with each other* (e.g. ``INT + DATE`` — both are in the arithmetic
           allowlist but numeric + temporal is invalid).

        Both layers are needed: layer 1 prevents the transform from hiding
        errors by silently converting invalid expressions, layer 2 detects
        semantic mismatches between valid-looking operands.
        """
        from graphglot.analysis import SemanticAnalyzer
        from graphglot.error import FeatureError, ParseError, TokenError, ValidationError

        # Stage 1: Tokenize
        try:
            lex = self.lexer(**opts)
            tokens = lex.tokenize(query)
        except (TokenError, FeatureError) as e:
            return ValidationResult(success=False, stage="lexer", error=e, query=query)

        # Stage 2: Parse
        try:
            parsed_expressions = self.parser(**opts).parse(tokens, query)
            expressions = [expr for expr in parsed_expressions if expr is not None]
        except (ParseError, FeatureError, ValidationError) as e:
            return ValidationResult(success=False, stage="parser", error=e, query=query)

        # Stage 3: Semantic analysis (on transformed copy for scope tracking)
        analysis_expressions = self.transform(expressions)
        analyzer = SemanticAnalyzer()
        diagnostics = []
        analysis_feature_ids: set[str] = set()
        for expr in analysis_expressions:
            result = analyzer.analyze(expr, self, disabled_rules=disabled_rules)
            diagnostics.extend(result.diagnostics)
            analysis_feature_ids |= result.features

        # Resolve analysis feature IDs to Feature objects
        analysis_features: set[Feature] = set()
        for fid in analysis_feature_ids:
            try:
                analysis_features.add(get_feature(fid))
            except ValueError:
                pass

        if diagnostics:
            return ValidationResult(
                success=False,
                stage="analysis",
                diagnostics=diagnostics,
                features=analysis_features,
                expressions=expressions,
                query=query,
            )

        # Collect features from lexer + AST + analysis
        features = lex.get_required_features()
        for expr in expressions:
            features |= expr.get_required_features()
        features |= analysis_features

        return ValidationResult(
            success=True,
            stage="ok",
            features=features,
            expressions=expressions,
            query=query,
        )


def _validate_for_dialect(expressions: list[Expression], dialect: Dialect) -> None:
    """Validate AST features and run semantic analysis against *dialect*.

    Raises :class:`FeatureError` if any expression uses features that
    the dialect does not support.
    """
    from graphglot.analysis import SemanticAnalyzer
    from graphglot.ast.validation import validate_expression_features
    from graphglot.error import FeatureError

    for expression in expressions:
        validate_expression_features(expression, dialect, context="transpilation")

    _validate_functions_for_dialect(expressions, dialect)

    analyzer = SemanticAnalyzer()
    all_diagnostics = []
    for expression in expressions:
        result = analyzer.analyze(expression, dialect)
        all_diagnostics.extend(result.diagnostics)

    if all_diagnostics:
        msgs = "; ".join(d.message for d in all_diagnostics)
        feature_ids = ", ".join(sorted({d.feature_id for d in all_diagnostics}))
        raise FeatureError(
            msgs,
            feature_id=feature_ids,
        )


def _validate_functions_for_dialect(expressions: list[Expression], dialect: Dialect) -> None:
    """Reject Func nodes not in the target dialect's ``Parser.FUNCTIONS``."""
    from graphglot.ast.functions import Anonymous, Func
    from graphglot.error import FeatureError

    functions = getattr(getattr(dialect, "parser_class", None), "FUNCTIONS", None)
    if functions is None:
        return
    supported = set(functions.values())

    unsupported = []
    seen: set[type] = set()
    for expression in expressions:
        for node in expression.find_all(Func):
            if not isinstance(node, Func):  # pragma: no cover
                continue
            if isinstance(node, Anonymous):
                continue
            if type(node) not in supported and type(node) not in seen:
                seen.add(type(node))
                unsupported.append(node.func_name)

    if unsupported:
        unsupported.sort()
        name = dialect.__class__.__name__
        funcs = ", ".join(f"'{f}'" for f in unsupported)
        raise FeatureError(f"Unsupported function(s) for dialect '{name}': {funcs}")


DialectType = str | Dialect | type[Dialect] | None
