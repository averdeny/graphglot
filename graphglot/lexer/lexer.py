"""
Defines the Lexer class for parsing GQL queries into tokens.
"""

from __future__ import annotations

import typing as t

from graphglot import features as F
from graphglot.error import FeatureError, TokenError
from graphglot.features import Feature, get_feature
from graphglot.lexer.token import Token, TokenType
from graphglot.utils.trie import TrieResult, in_trie, new_trie

if t.TYPE_CHECKING:
    from graphglot.dialect.base import DialectType


class _Lexer(type):
    """
    Metaclass for the Lexer class. This is used to define the lexer attributes
    and methods in a more structured way.
    """

    def __new__(cls, clsname, bases, attrs):
        klass = super().__new__(cls, clsname, bases, attrs)

        def _convert_quotes(arr: list[str | tuple[str, str]]) -> dict[str, str]:
            return dict(
                (item, item) if isinstance(item, str) else (item[0], item[1]) for item in arr
            )

        def _quotes_to_format(
            token_type: TokenType, arr: list[str | tuple[str, str]]
        ) -> dict[str, tuple[str, TokenType]]:
            return {k: (v, token_type) for k, v in _convert_quotes(arr).items()}

        klass._QUOTES = _convert_quotes(klass.QUOTES)
        klass._IDENTIFIERS = _convert_quotes(klass.IDENTIFIERS)

        klass._FORMAT_STRINGS = {
            **{
                p + s: (e, TokenType.NATIONAL_STRING)
                for s, e in klass._QUOTES.items()
                for p in ("n", "N")
            },
            **{
                p + s: (e, TokenType.BYTE_STRING)
                for s, e in klass._QUOTES.items()
                for p in ("x", "X")
            },
            **{"@" + s: (e, TokenType.STRING) for s, e in klass._QUOTES.items()},
            # **_quotes_to_format(TokenType.BIT_STRING, klass.BIT_STRINGS),
            # **_quotes_to_format(TokenType.HEX_STRING, klass.HEX_STRINGS),
            # **_quotes_to_format(TokenType.RAW_STRING, klass.RAW_STRINGS),
            # **_quotes_to_format(TokenType.HEREDOC_STRING, klass.HEREDOC_STRINGS),
            # **_quotes_to_format(TokenType.UNICODE_STRING, klass.UNICODE_STRINGS),
        }

        klass._STRING_ESCAPES = set(klass.STRING_ESCAPES)
        klass._COMMENTS = {
            **dict(
                (comment, None) if isinstance(comment, str) else (comment[0], comment[1])
                for comment in klass.COMMENTS
            ),
            "{#": "#}",  # Ensure Jinja comments are tokenized correctly in all dialects
        }

        # This is key to the tokenization algorithm
        klass._KEYWORD_TRIE = new_trie(
            key.upper()
            for key in (
                *klass.KEYWORDS,
                *klass._COMMENTS,
                *klass._QUOTES,
                *klass._FORMAT_STRINGS,
            )
            if " " in key or any(single in key for single in klass.SINGLE_TOKENS)
        )

        return klass


class Lexer(metaclass=_Lexer):
    """
    Lexer for parsing GQL queries into tokens. This class is responsible for
    tokenizing the input query string and generating a list of tokens that can be
    used for further processing.
    """

    SINGLE_TOKENS: t.ClassVar[dict[str, TokenType]] = {
        ";": TokenType.SEMICOLON,
        "&": TokenType.AMPERSAND,
        "*": TokenType.ASTERISK,
        ":": TokenType.COLON,
        ",": TokenType.COMMA,
        "@": TokenType.COMMERCIAL_AT,
        "$": TokenType.DOLLAR_SIGN,
        "=": TokenType.EQUALS_OPERATOR,
        "!": TokenType.EXCLAMATION_MARK,
        ">": TokenType.RIGHT_ANGLE_BRACKET,
        "{": TokenType.LEFT_BRACE,
        "[": TokenType.LEFT_BRACKET,
        "(": TokenType.LEFT_PAREN,
        "<": TokenType.LEFT_ANGLE_BRACKET,
        "-": TokenType.MINUS_SIGN,
        "%": TokenType.PERCENT,
        ".": TokenType.PERIOD,
        "+": TokenType.PLUS_SIGN,
        "?": TokenType.QUESTION_MARK,
        "\\": TokenType.REVERSE_SOLIDUS,
        "}": TokenType.RIGHT_BRACE,
        "]": TokenType.RIGHT_BRACKET,
        ")": TokenType.RIGHT_PAREN,
        "/": TokenType.SOLIDUS,
        "~": TokenType.TILDE,
        # "_": TokenType.UNDERSCORE,
        "|": TokenType.VERTICAL_BAR,
        # String delimiters
        "'": TokenType.QUOTE,
        '"': TokenType.DOUBLE_QUOTE,
        "`": TokenType.GRAVE_ACCENT,
    }
    """
    Supported token types for single-character strings. These are used for
    performance reasons to avoid unnecessary string comparisons.
    """

    KEYWORDS: t.ClassVar[dict[str, TokenType]] = {
        "|+|": TokenType.MULTISET_ALTERNATION_OPERATOR,
        "]->": TokenType.BRACKET_RIGHT_ARROW,
        "]~>": TokenType.BRACKET_TILDE_RIGHT_ARROW,
        "||": TokenType.CONCATENATION_OPERATOR,
        "::": TokenType.DOUBLE_COLON,
        "$$": TokenType.DOUBLE_DOLLAR_SIGN,
        "--": TokenType.DOUBLE_MINUS_SIGN,
        "..": TokenType.DOUBLE_PERIOD,
        ">=": TokenType.GREATER_THAN_OR_EQUALS_OPERATOR,
        "<-": TokenType.LEFT_ARROW,
        "<~": TokenType.LEFT_ARROW_TILDE,
        "<-[": TokenType.LEFT_ARROW_BRACKET,
        "<~[": TokenType.LEFT_ARROW_TILDE_BRACKET,
        "<->": TokenType.LEFT_MINUS_RIGHT,
        "<-/": TokenType.LEFT_MINUS_SLASH,
        "<~/": TokenType.LEFT_TILDE_SLASH,
        "<=": TokenType.LESS_THAN_OR_EQUALS_OPERATOR,
        "-[": TokenType.MINUS_LEFT_BRACKET,
        "-/": TokenType.MINUS_SLASH,
        "<>": TokenType.NOT_EQUALS_OPERATOR,
        "->": TokenType.RIGHT_ARROW,
        "]-": TokenType.RIGHT_BRACKET_MINUS,
        "]~": TokenType.RIGHT_BRACKET_TILDE,
        "=>": TokenType.RIGHT_DOUBLE_ARROW,
        "/-": TokenType.SLASH_MINUS,
        "/->": TokenType.SLASH_MINUS_RIGHT,
        "/~": TokenType.SLASH_TILDE,
        "/~>": TokenType.SLASH_TILDE_RIGHT,
        "~[": TokenType.TILDE_LEFT_BRACKET,
        "~>": TokenType.TILDE_RIGHT_ARROW,
        "~/": TokenType.TILDE_SLASH,
        # Combined keywords
        "WITH ORDINALITY": TokenType.WITH_ORDINALITY,
        "WITH OFFSET": TokenType.WITH_OFFSET,
        "NULLS FIRST": TokenType.NULLS_FIRST,
        "NULLS LAST": TokenType.NULLS_LAST,
        "GROUP BY": TokenType.GROUP_BY,
        "ORDER BY": TokenType.ORDER_BY,
        "SESSION CLOSE": TokenType.SESSION_CLOSE,
        "SESSION SET": TokenType.SESSION_SET,
        "SESSION RESET": TokenType.SESSION_RESET,
        "START TRANSACTION": TokenType.START_TRANSACTION,
        # Keywords
        "ABS": TokenType.ABS,
        "ACOS": TokenType.ACOS,
        "ALL": TokenType.ALL,
        "ALL_DIFFERENT": TokenType.ALL_DIFFERENT,
        "AND": TokenType.AND,
        "ANY": TokenType.ANY,
        "ARRAY": TokenType.LIST,
        "AS": TokenType.AS,
        "ASC": TokenType.ASC,
        "ASCENDING": TokenType.ASC,
        "ASIN": TokenType.ASIN,
        "AT": TokenType.AT,
        "ATAN": TokenType.ATAN,
        "AVG": TokenType.AVG,
        "BIG": TokenType.BIG,
        "BIGINT": TokenType.BIGINT,
        "BIG INTEGER": TokenType.BIGINT,
        "SIGNED BIG INTEGER": TokenType.BIGINT,
        "BINARY": TokenType.BINARY,
        "BOOL": TokenType.BOOL,
        "BOOLEAN": TokenType.BOOL,
        "BOTH": TokenType.BOTH,
        "BTRIM": TokenType.BTRIM,
        "BY": TokenType.BY,
        "BYTE_LENGTH": TokenType.BYTE_LENGTH,
        "BYTES": TokenType.BYTES,
        "CALL": TokenType.CALL,
        "CARDINALITY": TokenType.CARDINALITY,
        "CASE": TokenType.CASE,
        "CAST": TokenType.CAST,
        "CEIL": TokenType.CEIL,
        "CEILING": TokenType.CEIL,
        "CHAR": TokenType.CHAR,
        "CHAR_LENGTH": TokenType.CHAR_LENGTH,
        "CHARACTER_LENGTH": TokenType.CHAR_LENGTH,
        "CHARACTERISTICS": TokenType.CHARACTERISTICS,
        "CLOSE": TokenType.CLOSE,
        "COALESCE": TokenType.COALESCE,
        "COLLECT_LIST": TokenType.COLLECT_LIST,
        "COMMIT": TokenType.COMMIT,
        "COPY": TokenType.COPY,
        "COS": TokenType.COS,
        "COSH": TokenType.COSH,
        "COT": TokenType.COT,
        "COUNT": TokenType.COUNT,
        "CREATE": TokenType.CREATE,
        "CURRENT_DATE": TokenType.CURRENT_DATE,
        "CURRENT_GRAPH": TokenType.CURRENT_GRAPH,
        "CURRENT_PROPERTY_GRAPH": TokenType.CURRENT_GRAPH,
        "CURRENT_SCHEMA": TokenType.CURRENT_SCHEMA,
        "CURRENT_TIME": TokenType.CURRENT_TIME,
        "CURRENT_TIMESTAMP": TokenType.CURRENT_TIMESTAMP,
        "DATE": TokenType.DATE,
        "DATETIME": TokenType.DATETIME,
        "DAY": TokenType.DAY,
        "DEC": TokenType.DEC,
        "DECIMAL": TokenType.DECIMAL,
        "DEGREES": TokenType.DEGREES,
        "DELETE": TokenType.DELETE,
        "DESC": TokenType.DESC,
        "DESCENDING": TokenType.DESC,
        "DETACH": TokenType.DETACH,
        "DISTINCT": TokenType.DISTINCT,
        "DOUBLE": TokenType.DOUBLE,
        "DOUBLE PRECISION": TokenType.DOUBLE,
        "DROP": TokenType.DROP,
        "DURATION": TokenType.DURATION,
        "DURATION_BETWEEN": TokenType.DURATION_BETWEEN,
        "ELEMENT_ID": TokenType.ELEMENT_ID,
        "ELSE": TokenType.ELSE,
        "END": TokenType.END,
        "EXCEPT": TokenType.EXCEPT,
        "EXISTS": TokenType.EXISTS,
        "EXP": TokenType.EXP,
        "FALSE": TokenType.FALSE,
        "FILTER": TokenType.FILTER,
        "FINISH": TokenType.FINISH,
        "FLOAT": TokenType.FLOAT,
        "FLOAT16": TokenType.FLOAT16,
        "FLOAT32": TokenType.FLOAT32,
        "FLOAT64": TokenType.FLOAT64,
        "FLOAT128": TokenType.FLOAT128,
        "FLOAT256": TokenType.FLOAT256,
        "FLOOR": TokenType.FLOOR,
        "FOR": TokenType.FOR,
        "FROM": TokenType.FROM,
        "GROUP": TokenType.GROUP,
        "HAVING": TokenType.HAVING,
        "HOME_GRAPH": TokenType.HOME_GRAPH,
        "HOME_PROPERTY_GRAPH": TokenType.HOME_GRAPH,
        "HOME_SCHEMA": TokenType.HOME_SCHEMA,
        "HOUR": TokenType.HOUR,
        "IF": TokenType.IF,
        "IMPLIES": TokenType.IMPLIES,
        "IN": TokenType.IN,
        "INSERT": TokenType.INSERT,
        "INT": TokenType.INT,
        "INTEGER": TokenType.INT,
        "SIGNED INTEGER": TokenType.INT,
        "INT8": TokenType.INT8,
        "INTEGER8": TokenType.INT8,
        "SIGNED INTEGER8": TokenType.INT8,
        "INT16": TokenType.INT16,
        "INTEGER16": TokenType.INT16,
        "SIGNED INTEGER16": TokenType.INT16,
        "INT32": TokenType.INT32,
        "INTEGER32": TokenType.INT32,
        "SIGNED INTEGER32": TokenType.INT32,
        "INTERVAL": TokenType.INTERVAL,
        "IS": TokenType.IS,
        "INT64": TokenType.INT64,
        "INTEGER64": TokenType.INT64,
        "SIGNED INTEGER64": TokenType.INT64,
        "INT128": TokenType.INT128,
        "INTEGER128": TokenType.INT128,
        "SIGNED INTEGER128": TokenType.INT128,
        "INT256": TokenType.INT256,
        "INTEGER256": TokenType.INT256,
        "SIGNED INTEGER256": TokenType.INT256,
        "INTERSECT": TokenType.INTERSECT,
        "LEADING": TokenType.LEADING,
        "LEFT": TokenType.LEFT,
        "LET": TokenType.LET,
        "LIKE": TokenType.LIKE,
        "LIMIT": TokenType.LIMIT,
        "LIST": TokenType.LIST,
        "LN": TokenType.LN,
        "LOCAL": TokenType.LOCAL,
        "LOCAL_DATETIME": TokenType.LOCAL_DATETIME,
        "LOCAL_TIME": TokenType.LOCAL_TIME,
        "LOCAL_TIMESTAMP": TokenType.LOCAL_TIMESTAMP,
        "LOG": TokenType.LOG,
        "LOG10": TokenType.LOG10,
        "LOWER": TokenType.LOWER,
        "LTRIM": TokenType.LTRIM,
        "MATCH": TokenType.MATCH,
        "MAX": TokenType.MAX,
        "MIN": TokenType.MIN,
        "MINUTE": TokenType.MINUTE,
        "MOD": TokenType.MOD,
        "MONTH": TokenType.MONTH,
        "NEXT": TokenType.NEXT,
        "NODETACH": TokenType.NODETACH,
        "NORMALIZE": TokenType.NORMALIZE,
        "NOT": TokenType.NOT,
        "NOTHING": TokenType.NOTHING,
        "NULL": TokenType.NULL,
        "NULLS": TokenType.NULLS,
        "NULLIF": TokenType.NULLIF,
        "OCTET_LENGTH": TokenType.BYTE_LENGTH,
        "OF": TokenType.OF,
        "OFFSET": TokenType.OFFSET,
        "OPTIONAL": TokenType.OPTIONAL,
        "OR": TokenType.OR,
        "ORDER": TokenType.ORDER,
        "OTHERWISE": TokenType.OTHERWISE,
        "PARAMETER": TokenType.PARAMETER,
        "PARAMETERS": TokenType.PARAMETERS,
        "PATH": TokenType.PATH,
        "PATH_LENGTH": TokenType.PATH_LENGTH,
        "PATHS": TokenType.PATHS,
        "PERCENTILE_CONT": TokenType.PERCENTILE_CONT,
        "PERCENTILE_DISC": TokenType.PERCENTILE_DISC,
        "POWER": TokenType.POWER,
        "PRECISION": TokenType.PRECISION,
        "PROPERTY_EXISTS": TokenType.PROPERTY_EXISTS,
        "RADIANS": TokenType.RADIANS,
        "REAL": TokenType.REAL,
        "RECORD": TokenType.RECORD,
        "REMOVE": TokenType.REMOVE,
        "REPLACE": TokenType.REPLACE,
        "RESET": TokenType.RESET,
        "RETURN": TokenType.RETURN,
        "RIGHT": TokenType.RIGHT,
        "ROLLBACK": TokenType.ROLLBACK,
        "RTRIM": TokenType.RTRIM,
        "SAME": TokenType.SAME,
        "SCHEMA": TokenType.SCHEMA,
        "SECOND": TokenType.SECOND,
        "SELECT": TokenType.SELECT,
        "SESSION": TokenType.SESSION,
        "SESSION_USER": TokenType.SESSION_USER,
        "SET": TokenType.SET,
        "SIGNED": TokenType.SIGNED,
        "SIN": TokenType.SIN,
        "SINH": TokenType.SINH,
        "SIZE": TokenType.SIZE,
        "SKIP": TokenType.OFFSET,
        "SMALL": TokenType.SMALL,
        "SMALLINT": TokenType.SMALLINT,
        "SMALL INTEGER": TokenType.SMALLINT,
        "SIGNED SMALL INTEGER": TokenType.SMALLINT,
        "SQRT": TokenType.SQRT,
        "START": TokenType.START,
        "STDDEV_POP": TokenType.STDDEV_POP,
        "STDDEV_SAMP": TokenType.STDDEV_SAMP,
        "STRING": TokenType.STRING,
        "SUM": TokenType.SUM,
        "TAN": TokenType.TAN,
        "TANH": TokenType.TANH,
        "THEN": TokenType.THEN,
        "TIME": TokenType.TIME,
        "TIMESTAMP": TokenType.TIMESTAMP,
        "TRAILING": TokenType.TRAILING,
        "TRIM": TokenType.TRIM,
        "TRUE": TokenType.TRUE,
        "TYPED": TokenType.TYPED,
        "UBIGINT": TokenType.UBIGINT,
        "UNSIGNED BIG INTEGER": TokenType.UBIGINT,
        "UINT": TokenType.UINT,
        "UNSIGNED INTEGER": TokenType.UINT,
        "UINT8": TokenType.UINT8,
        "UNSIGNED INTEGER8": TokenType.UINT8,
        "UINT16": TokenType.UINT16,
        "UNSIGNED INTEGER16": TokenType.UINT16,
        "UINT32": TokenType.UINT32,
        "UNSIGNED INTEGER32": TokenType.UINT32,
        "UINT64": TokenType.UINT64,
        "UNSIGNED INTEGER64": TokenType.UINT64,
        "UINT128": TokenType.UINT128,
        "UNSIGNED INTEGER128": TokenType.UINT128,
        "UINT256": TokenType.UINT256,
        "UNSIGNED INTEGER256": TokenType.UINT256,
        "UNION": TokenType.UNION,
        "UNKNOWN": TokenType.UNKNOWN,
        "UNSIGNED": TokenType.UNSIGNED,
        "UPPER": TokenType.UPPER,
        "USE": TokenType.USE,
        "USMALLINT": TokenType.USMALLINT,
        "UNSIGNED SMALL INTEGER": TokenType.USMALLINT,
        "VALUE": TokenType.VALUE,
        "VARBINARY": TokenType.VARBINARY,
        "VARCHAR": TokenType.VARCHAR,
        "VARIABLE": TokenType.VARIABLE,
        "WHEN": TokenType.WHEN,
        "WHERE": TokenType.WHERE,
        "WITH": TokenType.WITH,
        "XOR": TokenType.XOR,
        "YEAR": TokenType.YEAR,
        "YIELD": TokenType.YIELD,
        "ZONED": TokenType.ZONED,
        "ZONED_DATETIME": TokenType.ZONED_DATETIME,
        "ZONED_TIME": TokenType.ZONED_TIME,
        "ABSTRACT": TokenType.ABSTRACT,
        "AGGREGATE": TokenType.AGGREGATE,
        "AGGREGATES": TokenType.AGGREGATES,
        "ALTER": TokenType.ALTER,
        "CATALOG": TokenType.CATALOG,
        "CLEAR": TokenType.CLEAR,
        "CLONE": TokenType.CLONE,
        "CONSTRAINT": TokenType.CONSTRAINT,
        "CURRENT_ROLE": TokenType.CURRENT_ROLE,
        "CURRENT_USER": TokenType.CURRENT_USER,
        "DATA": TokenType.DATA,
        "DIRECTORY": TokenType.DIRECTORY,
        "DRYRUN": TokenType.DRYRUN,
        "EXACT": TokenType.EXACT,
        "EXISTING": TokenType.EXISTING,
        "FUNCTION": TokenType.FUNCTION,
        "GQLSTATUS": TokenType.GQLSTATUS,
        "GRANT": TokenType.GRANT,
        "INSTANT": TokenType.INSTANT,
        "INFINITY": TokenType.INFINITY,
        "NUMBER": TokenType.NUMBER,
        "NUMERIC": TokenType.NUMERIC,
        "ON": TokenType.ON,
        "OPEN": TokenType.OPEN,
        "PARTITION": TokenType.PARTITION,
        "PROCEDURE": TokenType.PROCEDURE,
        "PRODUCT": TokenType.PRODUCT,
        "PROJECT": TokenType.PROJECT,
        "QUERY": TokenType.QUERY,
        "RECORDS": TokenType.RECORDS,
        "REFERENCE": TokenType.REFERENCE,
        "RENAME": TokenType.RENAME,
        "REVOKE": TokenType.REVOKE,
        "SUBSTRING": TokenType.SUBSTRING,
        "SYSTEM_USER": TokenType.SYSTEM_USER,
        "TEMPORAL": TokenType.TEMPORAL,
        "UNIQUE": TokenType.UNIQUE,
        "UNIT": TokenType.UNIT,
        "VALUES": TokenType.VALUES,
        "WHITESPACE": TokenType.WHITESPACE,
        "ACYCLIC": TokenType.ACYCLIC,
        "BINDING": TokenType.BINDING,
        "BINDINGS": TokenType.BINDINGS,
        "CONNECTING": TokenType.CONNECTING,
        "DESTINATION": TokenType.DESTINATION,
        "DIFFERENT": TokenType.DIFFERENT,
        "DIRECTED": TokenType.DIRECTED,
        "EDGE": TokenType.EDGE,
        "EDGES": TokenType.EDGES,
        "ELEMENT": TokenType.ELEMENT,
        "ELEMENTS": TokenType.ELEMENTS,
        "FIRST": TokenType.FIRST,
        "GRAPH": TokenType.GRAPH,
        "PROPERTY GRAPH": TokenType.GRAPH,
        "GROUPS": TokenType.GROUPS,
        "KEEP": TokenType.KEEP,
        "LABEL": TokenType.LABEL,
        "LABELED": TokenType.LABELED,
        "LABELS": TokenType.LABELS,
        "LAST": TokenType.LAST,
        "NFC": TokenType.NFC,
        "NFD": TokenType.NFD,
        "NFKC": TokenType.NFKC,
        "NFKD": TokenType.NFKD,
        "NO": TokenType.NO,
        "NODE": TokenType.NODE,
        "NORMALIZED": TokenType.NORMALIZED,
        "ONLY": TokenType.ONLY,
        "ORDINALITY": TokenType.ORDINALITY,
        "PROPERTY": TokenType.PROPERTY,
        "READ": TokenType.READ,
        "RELATIONSHIP": TokenType.EDGE,
        "RELATIONSHIPS": TokenType.EDGES,
        "REPEATABLE": TokenType.REPEATABLE,
        "SHORTEST": TokenType.SHORTEST,
        "SIMPLE": TokenType.SIMPLE,
        "SOURCE": TokenType.SOURCE,
        "TABLE": TokenType.TABLE,
        "BINDING TABLE": TokenType.TABLE,
        "TEMP": TokenType.TEMP,
        "TO": TokenType.TO,
        "TRAIL": TokenType.TRAIL,
        "TRANSACTION": TokenType.TRANSACTION,
        "TYPE": TokenType.TYPE,
        "UNDIRECTED": TokenType.UNDIRECTED,
        "VERTEX": TokenType.NODE,
        "WALK": TokenType.WALK,
        "WITHOUT": TokenType.WITHOUT,
        "WRITE": TokenType.WRITE,
        "ZONE": TokenType.ZONE,
    }
    """
    Supported keywords for the GQL dialect. These are used to identify keywords in the
    input query string.
    """

    WHITE_SPACE: t.ClassVar[dict[str, TokenType]] = {
        " ": TokenType.SPACE,
        "\t": TokenType.SPACE,
        "\f": TokenType.SPACE,
        "\n": TokenType.BREAK,
        "\r": TokenType.BREAK,
        "\r\n": TokenType.BREAK,
    }
    """
    White space characters that will be skipped during tokenization. This includes
    spaces, tabs, and line breaks.
    """

    COMMENTS: t.ClassVar[list[str | tuple[str, str]]] = ["--", "//", ("/*", "*/")]
    """
    Supported comment delimiters. These are used to identify comments in the input
    query string. The first element is the start delimiter, and the second element is
    the end delimiter. If the second element is None, it means that the comment is a
    single-line comment and does not have an end delimiter.

    Jinja comments (e.g. {{# comment #}}) are also supported and handled in the metadata
    class.
    """

    QUOTES: t.ClassVar[list[tuple[str, str] | str]] = ["'", '"']
    """
    Supported string delimiters used to identify strings in the input query string.
    """

    IDENTIFIER_ESCAPES: t.ClassVar[list[str]] = []
    """
    The strings in this list can always be used as escapes, regardless of the surrounding
    identifier delimiters. By default, the closing delimiter is assumed to also act as an
    identifier escape
    """

    IDENTIFIERS: t.ClassVar[list[str | tuple[str, str]]] = ["`"]
    """
    Supported identifier delimiters used to identify identifiers in the input query string.
    """

    VAR_SINGLE_TOKENS: t.ClassVar[set[str]] = set()
    """
    Single-character tokens that can be used as variable delimiters. These are used to
    identify variables in the input query string. By default, this is empty.
    """

    ERROR_CONTEXT_WINDOW: t.ClassVar[int] = 50
    """
    The number of characters to include in the error context when raising a TokenError.
    This is used to provide more context about the error that occurred during tokenization.
    """

    STRING_ESCAPES: t.ClassVar[list[str]] = ["'"]

    STRING_ESCAPES_ALLOWED_IN_RAW_STRINGS = True
    """
    Boolean flag that indicates whether string escape characters function as such when
    placed within raw strings. This is used to determine how to handle escape characters
    in raw strings during tokenization.
    """

    NESTED_COMMENTS = True
    """
    Boolean flag that indicates whether nested comments are allowed in the GQL dialect.
    """

    # Digit character sets for radix-prefixed numeric literals
    HEX_DIGITS: t.ClassVar[str] = "0123456789abcdefABCDEF"
    OCTAL_DIGITS: t.ClassVar[str] = "01234567"
    BINARY_DIGITS: t.ClassVar[str] = "01"

    __slots__ = (
        "_char",
        "_col",
        "_comments",
        "_current",
        "_end",
        "_line",
        "_peek",
        "_prev_token_line",
        "_required_features",
        "_start",
        "dialect",
        "query",
        "size",
        "tokens",
    )

    def __init__(self, dialect: DialectType | None = None) -> None:
        """Lexer initializer.

        Args:
            dialect: The dialect to use for lexing.
        """
        from graphglot.dialect.base import Dialect

        self.dialect = Dialect.get_or_raise(dialect)

        self.reset()

    def reset(self) -> None:
        """Reset the lexer state."""

        self.query = ""  # The GQL query string to tokenize
        self.size = 0  # Length of the query
        self.tokens: list[Token] = []  # List of tokens generated
        self._current = 0  # Current position in the query
        self._start = 0  # Start position of the current token
        self._line = 1  # Current line number
        self._col = 1  # Current column number
        self._comments: list[str] = []  # List of comments found in the query

        self._char = ""  # Current character being processed
        self._end = False  # Flag to indicate if the end of the query has been reached
        self._peek = ""  # Next character to be processed
        self._prev_token_line = 0  # Line number of the previous token
        self._required_features: set[Feature] = set()  # type: ignore[assignment]

    def require_feature(self, feature: str | Feature) -> None:
        """Require a feature for the current token being scanned.

        This method mirrors Expression.require_feature() in the AST layer.
        Currently raises FeatureError immediately if feature is unsupported,
        but could be modified to collect features for deferred validation.

        Args:
            feature: The feature ID to require (string or Feature).

        Raises:
            FeatureError: If the feature is not supported by the dialect.
        """
        if isinstance(feature, str):
            feature = get_feature(feature)

        if not self.dialect.is_feature_supported(feature):
            raise FeatureError(
                f"Feature '{feature}' ({feature.description}) is not supported by this dialect "
                f"(line {self._line}, col {self._col}).",
                feature_id=str(feature),
                line=self._line,
                col=self._col,
                start_offset=self._start,
                end_offset=self._current,
            )

        # Track the feature (useful for introspection even if we raise immediately)
        self._required_features.add(feature)

    def get_required_features(self) -> set[Feature]:  # type: ignore[type-arg]
        """Get all features required by tokens scanned so far.

        Returns:
            A set of Feature objects representing features required by the query.
        """
        return set(self._required_features)

    def tokenize(self, query: str) -> list[Token]:
        """Tokenize the given query string.

        Args:
            query: The GQL query string to tokenize.

        Returns:
            A list of tokens.
        """

        self.reset()
        self.query = query
        self.size = len(query)

        try:
            self._scan()
        except (TokenError, FeatureError):
            # Let TokenError and FeatureError pass through without re-wrapping
            raise
        except Exception as e:
            start = max(0, self._current - self.ERROR_CONTEXT_WINDOW)
            end = min(self.size, self._current + self.ERROR_CONTEXT_WINDOW)
            context = query[start:end]
            raise TokenError(
                f"Unexpected character near: '{context}'",
                line=self._line,
                col=self._col,
                start_offset=self._start,
                end_offset=self._current,
            ) from e

        return self.tokens

    def _scan(self, until: t.Callable | None = None) -> None:
        """Scan the query string and generate tokens.

        Args:
            until: A callable to determine when to stop scanning.
        """

        while self.size and not self._end:
            current = self._current

            # Skip spaces rather than iteratively calling advance() for performance reasons
            while current < self.size:
                char = self.query[current]

                if char.isspace() and self.WHITE_SPACE.get(char) is TokenType.SPACE:
                    current += 1
                else:
                    break

            offset = current - self._current if current > self._current else 1

            self._start = current
            self._advance(offset)

            if not self._char.isspace():
                if self._char.isdigit() or (
                    self._char == "."
                    and self._current < self.size
                    and self.query[self._current].isdigit()
                ):
                    self._scan_number()
                elif self._char in self._IDENTIFIERS:
                    self._scan_identifier(self._IDENTIFIERS[self._char])
                else:
                    self._scan_keywords()

            if until and until():
                break

        # Attach comments to the last token if any exist
        if self.tokens and self._comments:
            self.tokens[-1].comments.extend(self._comments)

    def _chars(self, size: int) -> str:
        """Get the characters from the query string.

        Args:
            size: The number of characters to get.

        Returns:
            The characters from the query string.
        """

        if size == 1:
            return self._char

        start = self._current - 1
        end = start + size

        return self.query[start:end] if end <= self.size else ""

    def _advance(self, i: int = 1, alnum: bool = False) -> None:
        """Advance the current position in the query.

        Args:
            i: The number of characters to advance.
            alnum: Whether to include alphanumeric characters. Used for performance reasons.
        """

        if self.WHITE_SPACE.get(self._char) is TokenType.BREAK:
            # Ensures we don't count an extra line if we get a \r\n line break sequence
            if not (self._char == "\r" and self._peek == "\n"):
                self._col = 1
                self._line += 1
        else:
            self._col += i

        self._current += i
        self._end = self._current >= self.size
        self._char = self.query[self._current - 1]
        self._peek = "" if self._end else self.query[self._current]

        if alnum and self._char.isalnum():
            # Local variables instead of attributes here for better performance
            _col = self._col
            _current = self._current
            _end = self._end
            _peek = self._peek

            while _peek.isalnum():
                _col += 1
                _current += 1
                _end = _current >= self.size
                _peek = "" if _end else self.query[_current]

            self._col = _col
            self._current = _current
            self._end = _end
            self._peek = _peek
            self._char = self.query[_current - 1]

    @property
    def _text(self) -> str:
        return self.query[self._start : self._current]

    def _add(self, token_type: TokenType, text: str | None = None) -> None:
        """Add a token to the list of tokens.

        Args:
            token_type: The type of the token.
            text: The text of the token.
        """
        self._prev_token_line = self._line

        # If there are some collected comments waiting (self._comments is not empty)
        # and the token being added now is a SEMICOLON (;)
        if self._comments and token_type == TokenType.SEMICOLON and self.tokens:
            # Then,iInstead of attaching those comments to the semicolon token, which
            # carries no semantic meaning, we attach them to the previous token
            self.tokens[-1].comments.extend(self._comments)
            # Finally clear the collected comments (self._comments = []).
            self._comments = []

        self.tokens.append(
            Token(
                token_type,
                text=self._text if text is None else text,
                line=self._line,
                col=self._col,
                start=self._start,
                end=self._current - 1,
                comments=self._comments,
            )
        )
        self._comments = []

    def _scan_keywords(self) -> None:
        size = 0
        word = None
        chars = self._text
        char = chars
        prev_space = False
        skip = False
        trie = self._KEYWORD_TRIE
        single_token = char in self.SINGLE_TOKENS

        while chars:
            if skip:
                result = TrieResult.PREFIX
            else:
                result, trie = in_trie(trie, char.upper())

            if result == TrieResult.FAILED:
                break
            if result == TrieResult.EXISTS:
                word = chars

            end = self._current + size
            size += 1

            if end < self.size:
                char = self.query[end]
                single_token = single_token or char in self.SINGLE_TOKENS
                is_space = char.isspace()

                if not is_space or not prev_space:
                    if is_space:
                        char = " "
                    chars += char
                    prev_space = is_space
                    skip = False
                else:
                    skip = True
            else:
                char = ""
                break

        if word:
            if self._scan_string(word):
                return
            if self._scan_comment(word):
                return
            if prev_space or single_token or not char:
                self._advance(size - 1)
                word = word.upper()
                self._add(self.KEYWORDS[word], text=word)
                return

        if self._char in self.SINGLE_TOKENS:
            self._add(self.SINGLE_TOKENS[self._char], text=self._char)
            return

        self._scan_var()

    def _scan_comment(self, comment_start: str) -> bool:
        """Scan for a comment token.

        Args:
            comment_start: The starting character of the comment.

        Returns:
            True if a comment was found, False otherwise.
        """

        # REMINDER: self._COMMENTS is a dictionary where the keys are the comment start
        # delimiters and the values are the comment end delimiters. If the value is None,
        # it means that the comment is a single-line comment and does not have an end
        # delimiter.

        # Early exit if the comment start is not in the comments dictionary
        if comment_start not in self._COMMENTS:
            return False

        if comment_start == "--":
            self.require_feature(F.GB02)
        elif comment_start == "//":
            self.require_feature(F.GB03)

        comment_start_line = self._line  # Line where the comment starts
        comment_start_size = len(comment_start)  # Size of the comment start
        comment_end = self._COMMENTS[comment_start]  # End delimiter of the comment

        if comment_end:
            # Skip the comment's start delimiter
            self._advance(comment_start_size)

            comment_count = 1
            comment_end_size = len(comment_end)

            while not self._end:
                if self._chars(comment_end_size) == comment_end:
                    comment_count -= 1
                    if not comment_count:
                        break

                self._advance(alnum=True)

                # Nested comments are allowed by some dialects, e.g. databricks, duckdb, postgres
                if (
                    self.NESTED_COMMENTS
                    and not self._end
                    and self._chars(comment_end_size) == comment_start
                ):
                    self._advance(comment_start_size)
                    comment_count += 1

            self._comments.append(self._text[comment_start_size : -comment_end_size + 1])
            self._advance(comment_end_size - 1)
        else:
            while not self._end and self.WHITE_SPACE.get(self._peek) is not TokenType.BREAK:
                self._advance(alnum=True)
            self._comments.append(self._text[comment_start_size:])

        # Leading comment is attached to the succeeding token, whilst trailing
        # comment to the preceding. Multiple consecutive comments are preserved by
        # appending them to the current comments list.
        if comment_start_line == self._prev_token_line:
            self.tokens[-1].comments.extend(self._comments)
            self._comments = []
            self._prev_token_line = self._line

        return True

    def _scan_string(self, start: str) -> bool:
        """Scan for a string token.

        Args:
            start: The starting character of the string.

        Returns:
            True if a string was found, False otherwise.
        """
        token_type = TokenType.STRING

        if start in self._QUOTES:
            end = self._QUOTES[start]
        elif start in self._FORMAT_STRINGS:
            end, token_type = self._FORMAT_STRINGS[start]

            # Here we could handle the different types of strings (e.g. HEREDOC,
            # HEX_STRING, etc.) if needed.

        else:
            return False

        no_escape = start.startswith("@")
        if no_escape:
            self.require_feature(F.GL11)

        self._advance(len(start))
        text = self._extract_string(
            end,
            escapes=set() if no_escape else None,
            raw_string=token_type == TokenType.RAW_STRING,
        )

        self._add(token_type, text)
        return True

    def _scan_identifier(self, identifier_end: str) -> None:
        self._advance()
        text = self._extract_string(
            identifier_end, escapes=set(self.IDENTIFIER_ESCAPES) | {identifier_end}
        )
        self._add(TokenType.VAR, text)

    def _scan_var(self) -> None:
        while True:
            char = self._peek.strip()
            if not char:
                break
            if char in self.VAR_SINGLE_TOKENS:
                self._advance(alnum=True)
            elif char in self.SINGLE_TOKENS:
                break
            elif ("_" + char).isidentifier():
                # Valid identifier continuation (Unicode XID_Continue per §21.3)
                self._advance(alnum=True)
            else:
                break

        self._add(
            TokenType.VAR
            if self.tokens and self.tokens[-1].token_type == TokenType.PARAMETER
            else self.KEYWORDS.get(self._text.upper(), TokenType.VAR)
        )

    def _extract_string(
        self,
        delimiter: str,
        escapes: set[str] | None = None,
        raw_string: bool = False,
        raise_unmatched: bool = True,
    ) -> str:
        text = ""
        delim_size = len(delimiter)
        escapes = self._STRING_ESCAPES if escapes is None else escapes

        while True:
            if (
                not raw_string
                and self.dialect.UNESCAPED_SEQUENCES
                and self._peek
                and self._char in self.STRING_ESCAPES
            ):
                # Handle \uXXXX (4 hex) and \UXXXXXX (6 hex) unicode escapes
                if self._peek in ("u", "U"):
                    prefix = self._peek
                    expected = 4 if prefix == "u" else 6
                    self._advance(2)  # skip \ and u/U
                    hex_chars = ""
                    for _ in range(expected):
                        if self._end or self._char == delimiter:
                            raise TokenError(
                                f"Invalid unicode escape: \\{prefix}{hex_chars} "
                                f"(expected {expected} hex digits, got {len(hex_chars)})",
                                line=self._line,
                                col=self._current,
                                start_offset=self._start,
                                end_offset=self._current,
                            )
                        hex_chars += self._char
                        self._advance()
                    if not all(c in "0123456789abcdefABCDEF" for c in hex_chars):
                        raise TokenError(
                            f"Invalid unicode escape: \\{prefix}{hex_chars} "
                            f"(contains non-hex characters)",
                            line=self._line,
                            col=self._current,
                            start_offset=self._start,
                            end_offset=self._current,
                        )
                    text += chr(int(hex_chars, 16))
                    continue

                unescaped_sequence = self.dialect.UNESCAPED_SEQUENCES.get(self._char + self._peek)
                if unescaped_sequence:
                    self._advance(2)
                    text += unescaped_sequence
                    continue
            if (
                (self.STRING_ESCAPES_ALLOWED_IN_RAW_STRINGS or not raw_string)
                and self._char in escapes
                and (self._peek == delimiter or self._peek in escapes)
                and (self._char not in self._QUOTES or self._char == self._peek)
            ):
                if self._peek == delimiter:
                    text += self._peek
                else:
                    text += self._char + self._peek

                if self._current + 1 < self.size:
                    self._advance(2)
                else:
                    raise TokenError(
                        f"Unterminated string literal (line {self._line}, col {self._current})",
                        line=self._line,
                        col=self._current,
                        start_offset=self._start,
                        end_offset=self._current,
                    )
            else:
                if self._chars(delim_size) == delimiter:
                    if delim_size > 1:
                        self._advance(delim_size - 1)
                    break

                if self._end:
                    if not raise_unmatched:
                        return text + self._char

                    raise TokenError(
                        f"Unterminated string literal (line {self._line}, col {self._start})",
                        line=self._line,
                        col=self._start,
                        start_offset=self._start,
                        end_offset=self._current,
                    )

                current = self._current - 1
                self._advance(alnum=True)
                text += self.query[current : self._current - 1]

        return text

    def _scan_number(self) -> None:
        """Scan a numeric literal with feature validation."""

        # Check for radix prefix (0x, 0o, 0b)
        if self._char == "0" and self._current < self.size:
            next_char = self._peek.lower()

            if next_char == "x":
                self.require_feature(F.GL01)  # Hexadecimal literals
                self._scan_hex_digits()
                self._add(TokenType.NUMBER)
                return

            elif next_char == "o":
                self.require_feature(F.GL02)  # Octal literals
                self._scan_octal_digits()
                self._add(TokenType.NUMBER)
                return

            elif next_char == "b":
                self.require_feature(F.GL03)  # Binary literals
                self._scan_binary_digits()
                self._add(TokenType.NUMBER)
                return

        # Continue with decimal/float/scientific scanning...
        decimal = self._char == "."
        scientific = 0

        while True:
            if self._peek.isdigit():
                self._advance()
            elif self._peek == "." and not decimal:
                decimal = True
                self._advance()
            elif self._peek in ("-", "+") and scientific == 1:
                scientific += 1
                self._advance()
            elif self._peek.upper() == "E" and not scientific:
                scientific += 1
                self._advance()
            elif self._peek == "_" and self.dialect.NUMBERS_CAN_BE_UNDERSCORE_SEPARATED:
                # Enforce that underscores can only be used between digits.
                prev_is_digit = self._char.isdigit()
                next_is_digit = (
                    self._current + 1 < self.size and self.query[self._current + 1].isdigit()
                )
                if prev_is_digit and next_is_digit:
                    self._advance()
                else:
                    raise TokenError(
                        f"Invalid number literal: '{self._text}' "
                        f"(line {self._line}, col {self._current})",
                        line=self._line,
                        col=self._current,
                        start_offset=self._start,
                        end_offset=self._current,
                    )
            else:
                break

        # Check for numeric literal suffix
        if self._peek and self._peek.lower() in ("m", "f", "d"):
            suffix = self._peek.lower()

            if suffix == "m":
                # Exact number suffix
                if scientific:
                    self.require_feature(F.GL06)  # Exact number in scientific notation with suffix
                else:
                    self.require_feature(F.GL05)  # Exact number with suffix
            else:
                # Approximate number suffix (f or d)
                if suffix == "f":
                    self.require_feature(F.GL09)  # Optional float number suffix
                else:  # suffix == "d"
                    self.require_feature(F.GL10)  # Optional double number suffix

                if scientific:
                    self.require_feature(F.GL08)  # Approximate number in scientific notation
                else:
                    self.require_feature(F.GL07)  # Approximate number in common notation

            self._advance()  # consume suffix
        elif decimal and not scientific:
            self.require_feature(F.GL04)  # Exact number in common notation without suffix

        self._add(TokenType.NUMBER)

    def _scan_hex_digits(self) -> None:
        """Scan hexadecimal digits after 0x prefix."""
        self._advance()  # consume 'x' or 'X'

        if not self._peek or self._peek not in self.HEX_DIGITS:
            raise TokenError(
                f"Invalid hexadecimal literal (line {self._line})",
                line=self._line,
                start_offset=self._start,
                end_offset=self._current,
            )

        while self._peek and self._peek in self.HEX_DIGITS:
            self._advance()

        # Handle underscore separators if supported
        if self._peek == "_" and self.dialect.NUMBERS_CAN_BE_UNDERSCORE_SEPARATED:
            valid_chars = self.HEX_DIGITS + "_"
            while self._peek and self._peek in valid_chars:
                if self._peek == "_":
                    # Verify underscore is between valid hex digits
                    next_pos = self._current + 1
                    if next_pos >= self.size or self.query[next_pos] not in self.HEX_DIGITS:
                        raise TokenError(
                            f"Invalid hexadecimal literal: '{self._text}' "
                            f"(line {self._line}, col {self._current})",
                            line=self._line,
                            col=self._current,
                            start_offset=self._start,
                            end_offset=self._current,
                        )
                self._advance()

    def _scan_octal_digits(self) -> None:
        """Scan octal digits after 0o prefix."""
        self._advance()  # consume 'o' or 'O'

        if not self._peek or self._peek not in self.OCTAL_DIGITS:
            raise TokenError(
                f"Invalid octal literal (line {self._line})",
                line=self._line,
                start_offset=self._start,
                end_offset=self._current,
            )

        while self._peek and self._peek in self.OCTAL_DIGITS:
            self._advance()

        # Handle underscore separators if supported
        if self._peek == "_" and self.dialect.NUMBERS_CAN_BE_UNDERSCORE_SEPARATED:
            valid_chars = self.OCTAL_DIGITS + "_"
            while self._peek and self._peek in valid_chars:
                if self._peek == "_":
                    next_pos = self._current + 1
                    if next_pos >= self.size or self.query[next_pos] not in self.OCTAL_DIGITS:
                        raise TokenError(
                            f"Invalid octal literal: '{self._text}' "
                            f"(line {self._line}, col {self._current})",
                            line=self._line,
                            col=self._current,
                            start_offset=self._start,
                            end_offset=self._current,
                        )
                self._advance()

    def _scan_binary_digits(self) -> None:
        """Scan binary digits after 0b prefix."""
        self._advance()  # consume 'b' or 'B'

        if not self._peek or self._peek not in self.BINARY_DIGITS:
            raise TokenError(
                f"Invalid binary literal (line {self._line})",
                line=self._line,
                start_offset=self._start,
                end_offset=self._current,
            )

        while self._peek and self._peek in self.BINARY_DIGITS:
            self._advance()

        # Handle underscore separators if supported
        if self._peek == "_" and self.dialect.NUMBERS_CAN_BE_UNDERSCORE_SEPARATED:
            valid_chars = self.BINARY_DIGITS + "_"
            while self._peek and self._peek in valid_chars:
                if self._peek == "_":
                    next_pos = self._current + 1
                    if next_pos >= self.size or self.query[next_pos] not in self.BINARY_DIGITS:
                        raise TokenError(
                            f"Invalid binary literal: '{self._text}' "
                            f"(line {self._line}, col {self._current})",
                            line=self._line,
                            col=self._current,
                            start_offset=self._start,
                            end_offset=self._current,
                        )
                self._advance()

    _QUOTES: t.ClassVar[dict[str, str]]
    _IDENTIFIERS: t.ClassVar[dict[str, str]]
    _FORMAT_STRINGS: t.ClassVar[dict[str, tuple[str, TokenType]]]
    _STRING_ESCAPES: t.ClassVar[set[str]]
    _COMMENTS: t.ClassVar[dict[str, str | None]]
    _KEYWORD_TRIE: t.ClassVar[t.Any]
