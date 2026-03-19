"""
Defines the the Token, used to represent atomic elements of a query before they
are parsed into an AST.

Each token has a type, text, and position in the original query string.
"""

from __future__ import annotations

from enum import Enum, auto


class TokenType(Enum):
    """
    Types of tokens in graph queries. This correspond to base token types that
    should be present in all dialects.

    Each dialect may have its own set of tokens that extend this base set.
    """

    VAR = auto()  # Variable
    NATIONAL_STRING = auto()  # National string
    RAW_STRING = auto()  # Raw string
    BYTE_STRING = auto()  # Byte string

    # Special tokens
    SPACE = auto()  # Whitespace " ", "\t"
    BREAK = auto()  # Line break "\n", "\r"
    EOF = auto()  # End of file/input

    # Combined keywords
    WITH_ORDINALITY = auto()  # WITH ORDINALITY
    WITH_OFFSET = auto()  # WITH OFFSET
    NULLS_FIRST = auto()  # NULLS FIRST
    NULLS_LAST = auto()  # NULLS LAST
    GROUP_BY = auto()  # GROUP BY
    ORDER_BY = auto()  # ORDER BY
    SESSION_CLOSE = auto()  # SESSION CLOSE
    SESSION_SET = auto()  # SESSION SET
    SESSION_RESET = auto()  # SESSION RESET
    START_TRANSACTION = auto()  # START TRANSACTION

    # Characters
    SEMICOLON = auto()  # ;
    MULTISET_ALTERNATION_OPERATOR = auto()  # |+|
    BRACKET_RIGHT_ARROW = auto()  # ]->
    BRACKET_TILDE_RIGHT_ARROW = auto()  # ]~>
    CONCATENATION_OPERATOR = auto()  # ||
    DOUBLE_COLON = auto()  # ::
    DOUBLE_DOLLAR_SIGN = auto()  # $$
    DOUBLE_MINUS_SIGN = auto()  # --
    DOUBLE_PERIOD = auto()  # ..
    GREATER_THAN_OR_EQUALS_OPERATOR = auto()  # >=
    LEFT_ARROW = auto()  # <-
    LEFT_ARROW_TILDE = auto()  # <~
    LEFT_ARROW_BRACKET = auto()  # <-[
    LEFT_ARROW_TILDE_BRACKET = auto()  # <~[
    LEFT_MINUS_RIGHT = auto()  # <->
    LEFT_MINUS_SLASH = auto()  # <-/
    LEFT_TILDE_SLASH = auto()  # <~/
    LESS_THAN_OR_EQUALS_OPERATOR = auto()  # <=
    MINUS_LEFT_BRACKET = auto()  # -[
    MINUS_SLASH = auto()  # -/
    NOT_EQUALS_OPERATOR = auto()  # <>
    RIGHT_ARROW = auto()  # ->
    RIGHT_BRACKET_MINUS = auto()  # ]-
    RIGHT_BRACKET_TILDE = auto()  # ]~
    RIGHT_DOUBLE_ARROW = auto()  # =>
    SLASH_MINUS = auto()  # /-
    SLASH_MINUS_RIGHT = auto()  # /->
    SLASH_TILDE = auto()  # /~
    SLASH_TILDE_RIGHT = auto()  # /~>
    TILDE_LEFT_BRACKET = auto()  # ~[
    TILDE_RIGHT_ARROW = auto()  # ~>
    TILDE_SLASH = auto()  # ~/
    DOUBLE_SOLIDUS = auto()  # //
    BRACKETED_COMMENT_INTRODUCER = auto()  # /*
    BRACKETED_COMMENT_TERMINATOR = auto()  # */
    AMPERSAND = auto()  # &
    ASTERISK = auto()  # *
    COLON = auto()  # :
    COMMA = auto()  # ,
    COMMERCIAL_AT = auto()  # @
    DOLLAR_SIGN = auto()  # $
    DOUBLE_QUOTE = auto()  # "
    EQUALS_OPERATOR = auto()  # =
    EXCLAMATION_MARK = auto()  # !
    RIGHT_ANGLE_BRACKET = auto()  # >
    GRAVE_ACCENT = auto()  # `
    LEFT_BRACE = auto()  # {
    LEFT_BRACKET = auto()  # [
    LEFT_PAREN = auto()  # (
    LEFT_ANGLE_BRACKET = auto()  # <
    MINUS_SIGN = auto()  # -
    PERCENT = auto()  # %
    PERIOD = auto()  # .
    PLUS_SIGN = auto()  # +
    QUESTION_MARK = auto()  # ?
    QUOTE = auto()  # '
    REVERSE_SOLIDUS = auto()  # \
    RIGHT_BRACE = auto()  # }
    RIGHT_BRACKET = auto()  # ]
    RIGHT_PAREN = auto()  # )
    SOLIDUS = auto()  # /
    TILDE = auto()  # ~
    UNDERSCORE = auto()  # _
    VERTICAL_BAR = auto()  # |

    # Keywords - reserved words
    ABS = auto()
    ACOS = auto()
    ALL = auto()
    ALL_DIFFERENT = auto()
    AND = auto()
    ANY = auto()
    ARRAY = auto()
    AS = auto()
    ASC = auto()
    ASCENDING = auto()
    ASIN = auto()
    AT = auto()
    ATAN = auto()
    AVG = auto()
    BIG = auto()
    BIGINT = auto()
    BINARY = auto()
    BOOL = auto()
    BOOLEAN = auto()
    BOTH = auto()
    BTRIM = auto()
    BY = auto()
    BYTE_LENGTH = auto()
    BYTES = auto()
    CALL = auto()
    CARDINALITY = auto()
    CASE = auto()
    CAST = auto()
    CEIL = auto()
    CHAR = auto()
    CHAR_LENGTH = auto()
    CHARACTER_LENGTH = auto()
    CHARACTERISTICS = auto()
    CLOSE = auto()
    COALESCE = auto()
    COLLECT_LIST = auto()
    COMMIT = auto()
    COPY = auto()
    COS = auto()
    COSH = auto()
    COT = auto()
    COUNT = auto()
    CREATE = auto()
    CURRENT_DATE = auto()
    CURRENT_GRAPH = auto()
    CURRENT_PROPERTY_GRAPH = auto()
    CURRENT_SCHEMA = auto()
    CURRENT_TIME = auto()
    CURRENT_TIMESTAMP = auto()
    DATE = auto()
    DATETIME = auto()
    DAY = auto()
    DEC = auto()
    DECIMAL = auto()
    DEGREES = auto()
    DELETE = auto()
    DESC = auto()
    DESCENDING = auto()
    DETACH = auto()
    DISTINCT = auto()
    DOUBLE = auto()
    DROP = auto()
    DURATION = auto()
    DURATION_BETWEEN = auto()
    ELEMENT_ID = auto()
    ELSE = auto()
    END = auto()
    EXCEPT = auto()
    EXISTS = auto()
    EXP = auto()
    FALSE = auto()
    FILTER = auto()
    FINISH = auto()
    FLOAT = auto()
    FLOAT16 = auto()
    FLOAT32 = auto()
    FLOAT64 = auto()
    FLOAT128 = auto()
    FLOAT256 = auto()
    FLOOR = auto()
    FOR = auto()
    FROM = auto()
    GROUP = auto()
    HAVING = auto()
    HOME_GRAPH = auto()
    HOME_PROPERTY_GRAPH = auto()
    HOME_SCHEMA = auto()
    HOUR = auto()
    IF = auto()
    IMPLIES = auto()
    IN = auto()
    INSERT = auto()
    INT = auto()
    INTEGER = auto()
    INT8 = auto()
    INTEGER8 = auto()
    INT16 = auto()
    INTEGER16 = auto()
    INT32 = auto()
    INTERVAL = auto()
    IS = auto()
    INTEGER32 = auto()
    INT64 = auto()
    INTEGER64 = auto()
    INT128 = auto()
    INTEGER128 = auto()
    INT256 = auto()
    INTEGER256 = auto()
    INTERSECT = auto()
    LEADING = auto()
    LEFT = auto()
    LET = auto()
    LIKE = auto()
    LIMIT = auto()
    LIST = auto()
    LN = auto()
    LOCAL = auto()
    LOCAL_DATETIME = auto()
    LOCAL_TIME = auto()
    LOCAL_TIMESTAMP = auto()
    LOG = auto()
    LOG10 = auto()
    LOWER = auto()
    LTRIM = auto()
    MATCH = auto()
    MAX = auto()
    MIN = auto()
    MINUTE = auto()
    MOD = auto()
    MONTH = auto()
    NEXT = auto()
    NODETACH = auto()
    NORMALIZE = auto()
    NOT = auto()
    NOTHING = auto()
    NULL = auto()
    NULLS = auto()
    NULLIF = auto()
    OCTET_LENGTH = auto()
    OF = auto()
    OFFSET = auto()
    OPTIONAL = auto()
    OR = auto()
    ORDER = auto()
    OTHERWISE = auto()
    PARAMETER = auto()
    PARAMETERS = auto()
    PATH = auto()
    PATH_LENGTH = auto()
    PATHS = auto()
    PERCENTILE_CONT = auto()
    PERCENTILE_DISC = auto()
    POWER = auto()
    PRECISION = auto()
    PROPERTY_EXISTS = auto()
    RADIANS = auto()
    REAL = auto()
    RECORD = auto()
    REMOVE = auto()
    REPLACE = auto()
    RESET = auto()
    RETURN = auto()
    RIGHT = auto()
    ROLLBACK = auto()
    RTRIM = auto()
    SAME = auto()
    SCHEMA = auto()
    SECOND = auto()
    SELECT = auto()
    SESSION = auto()
    SESSION_USER = auto()
    SET = auto()
    SIGNED = auto()
    SIN = auto()
    SINH = auto()
    SIZE = auto()
    SKIP = auto()
    SMALL = auto()
    SMALLINT = auto()
    SQRT = auto()
    START = auto()
    STDDEV_POP = auto()
    STDDEV_SAMP = auto()
    STRING = auto()
    SUM = auto()
    TAN = auto()
    TANH = auto()
    THEN = auto()
    TIME = auto()
    TIMESTAMP = auto()
    TRAILING = auto()
    TRIM = auto()
    TRUE = auto()
    TYPED = auto()
    UBIGINT = auto()
    UINT = auto()
    UINT8 = auto()
    UINT16 = auto()
    UINT32 = auto()
    UINT64 = auto()
    UINT128 = auto()
    UINT256 = auto()
    UNION = auto()
    UNKNOWN = auto()
    UNSIGNED = auto()
    UPPER = auto()
    USE = auto()
    USMALLINT = auto()
    VALUE = auto()
    VARBINARY = auto()
    VARCHAR = auto()
    VARIABLE = auto()
    WHEN = auto()
    WHERE = auto()
    WITH = auto()
    XOR = auto()
    YEAR = auto()
    YIELD = auto()
    ZONED = auto()
    ZONED_DATETIME = auto()
    ZONED_TIME = auto()

    # Keywords - pre-reserved words
    ABSTRACT = auto()
    AGGREGATE = auto()
    AGGREGATES = auto()
    ALTER = auto()
    CATALOG = auto()
    CLEAR = auto()
    CLONE = auto()
    CONSTRAINT = auto()
    CURRENT_ROLE = auto()
    CURRENT_USER = auto()
    DATA = auto()
    DIRECTORY = auto()
    DRYRUN = auto()
    EXACT = auto()
    EXISTING = auto()
    FUNCTION = auto()
    GQLSTATUS = auto()
    GRANT = auto()
    INSTANT = auto()
    INFINITY = auto()
    NUMBER = auto()
    NUMERIC = auto()
    ON = auto()
    OPEN = auto()
    PARTITION = auto()
    PROCEDURE = auto()
    PRODUCT = auto()
    PROJECT = auto()
    QUERY = auto()
    RECORDS = auto()
    REFERENCE = auto()
    RENAME = auto()
    REVOKE = auto()
    SUBSTRING = auto()
    SYSTEM_USER = auto()
    TEMPORAL = auto()
    UNIQUE = auto()
    UNIT = auto()
    VALUES = auto()
    WHITESPACE = auto()

    # Keywords - non-reserved words
    ACYCLIC = auto()
    BINDING = auto()
    BINDINGS = auto()
    CONNECTING = auto()
    DESTINATION = auto()
    DIFFERENT = auto()
    DIRECTED = auto()
    EDGE = auto()
    EDGES = auto()
    ELEMENT = auto()
    ELEMENTS = auto()
    FIRST = auto()
    GRAPH = auto()
    GROUPS = auto()
    KEEP = auto()
    LABEL = auto()
    LABELED = auto()
    LABELS = auto()
    LAST = auto()
    NFC = auto()
    NFD = auto()
    NFKC = auto()
    NFKD = auto()
    NO = auto()
    NODE = auto()
    NORMALIZED = auto()
    ONLY = auto()
    ORDINALITY = auto()
    PROPERTY = auto()
    READ = auto()
    RELATIONSHIP = auto()
    RELATIONSHIPS = auto()
    REPEATABLE = auto()
    SHORTEST = auto()
    SIMPLE = auto()
    SOURCE = auto()
    TABLE = auto()
    TEMP = auto()
    TO = auto()
    TRAIL = auto()
    TRANSACTION = auto()
    TYPE = auto()
    UNDIRECTED = auto()
    VERTEX = auto()
    WALK = auto()
    WITHOUT = auto()
    WRITE = auto()
    ZONE = auto()

    # Dialect-specific tokens
    CARET = auto()  # ^ (Neo4j exponentiation operator)
    E = auto()  # For Neo4j's e() function equivalent to GQL's EXP(1) function
    INDEX = auto()  # INDEX (Cypher DDL)
    KEY = auto()  # KEY (Cypher constraint NODE KEY)
    REQUIRE = auto()  # REQUIRE (Cypher constraint)
    CONTAINS = auto()  # CONTAINS (Cypher string operator)
    CSV = auto()  # CSV keyword
    ENDS = auto()  # ENDS (part of ENDS WITH)
    EXPLAIN = auto()  # EXPLAIN query prefix
    FIELDTERMINATOR = auto()  # FIELDTERMINATOR for LOAD CSV
    FOREACH = auto()  # FOREACH clause
    HEADERS = auto()  # HEADERS (part of WITH HEADERS)
    LOAD = auto()  # LOAD keyword
    MERGE = auto()  # MERGE clause
    NONE_KW = auto()  # none() predicate function (avoids clash with NULL/NOTHING)
    PROFILE = auto()  # PROFILE query prefix
    REDUCE = auto()  # reduce() function
    ROUND = auto()  # ROUND() function (Cypher)
    ROWS = auto()  # ROWS (CALL IN TRANSACTIONS OF n ROWS)
    SINGLE = auto()  # single() predicate function
    STARTS = auto()  # STARTS (part of STARTS WITH)
    TILDE_EQUALS = auto()  # =~ (Cypher regex match operator)
    TRANSACTIONS = auto()  # TRANSACTIONS keyword
    UNWIND = auto()  # UNWIND clause
    KEYS = auto()  # KEYS() function (Cypher)
    NODES = auto()  # NODES() function (Cypher)
    PROPERTIES = auto()  # PROPERTIES() function (Cypher)
    RANGE = auto()  # RANGE() function (Cypher)
    TOBOOLEAN = auto()  # toBoolean() type conversion (Cypher)
    TOFLOAT = auto()  # toFloat() type conversion (Cypher)
    TOINTEGER = auto()  # toInteger() type conversion (Cypher)
    TOSTRING = auto()  # toString() type conversion (Cypher)
    TAIL = auto()  # tail() list function (Cypher)
    HEAD = auto()  # head() list function (Cypher)
    REVERSE = auto()  # reverse() list/string function (Cypher)
    RAND = auto()  # rand() numeric function (Cypher)
    STARTNODE = auto()  # startNode() function (Cypher)
    ENDNODE = auto()  # endNode() function (Cypher)
    SPLIT = auto()  # split() string function (Cypher)
    SIGN = auto()  # sign() numeric function (Cypher)
    TOLOWER = auto()  # toLower() string function (Cypher)
    TOUPPER = auto()  # toUpper() string function (Cypher)


class Token:
    __slots__ = (
        "col",
        "comments",
        "end",
        "line",
        "start",
        "text",
        "token_type",
    )

    def __init__(
        self,
        token_type: TokenType,
        text: str,
        line: int = 1,
        col: int = 1,
        start: int = 0,
        end: int = 0,
        comments: list[str] | None = None,
    ) -> None:
        """Token initializer.

        Args:
            token_type: The TokenType Enum.
            text: The text of the token.
            line: The line that the token ends on.
            col: The column that the token ends on.
            start: The start index of the token.
            end: The ending index of the token.
            comments: The comments to attach to the token.
        """
        self.token_type = token_type
        self.text = text
        self.line = line
        self.col = col
        self.start = start
        self.end = end
        self.comments = [] if comments is None else comments

    def __repr__(self) -> str:
        attributes = ", ".join(f"{k}: {getattr(self, k)}" for k in self.__slots__)
        return f"<Token {attributes}>"


def token_matches(token: Token | None, types: TokenType | set[TokenType]) -> bool:
    if token is None:
        return False
    if isinstance(types, set):
        return token.token_type in types
    if isinstance(types, TokenType):
        return token.token_type == types
    raise TypeError(f"Expected TokenType or set of TokenTypes, got {type(types).__name__}")


def sequence_matches(
    tokens: list[Token],
    start_index: int,
    sequence: tuple[TokenType, ...],
) -> bool:
    """Check if tokens starting at index match the sequence.

    Args:
        tokens: List of tokens to check against.
        start_index: Index to start matching from.
        sequence: Tuple of TokenTypes to match.

    Returns:
        True if tokens starting at start_index match the sequence.
    """
    for i, expected_type in enumerate(sequence):
        idx = start_index + i
        if idx >= len(tokens):
            return False
        if tokens[idx].token_type != expected_type:
            return False
    return True
