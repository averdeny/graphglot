"""Parser module for GraphGlot - recursive descent parsing of token streams into AST."""

from __future__ import annotations

import logging
import sys
import typing as t

from dataclasses import dataclass

from graphglot import ast
from graphglot.error import ErrorLevel, ParseError, _LazyParseError, concat_messages, merge_errors
from graphglot.lexer import Token, TokenType, token_matches
from graphglot.parser.registry import ParserKey, get_registry
from graphglot.utils.helper import seq_get

if t.TYPE_CHECKING:
    from graphglot.dialect.base import DialectType

logger = logging.getLogger(__name__)
T = t.TypeVar("T")


def _parser_description(parser_func: t.Callable) -> str | None:
    """Get human-readable description for a parser function."""
    desc = getattr(parser_func, "__description__", None)
    if desc:
        return desc
    name = getattr(parser_func, "__name__", "")
    if name and not name.startswith("<"):  # skip <lambda>
        # Convert _parse__foo_bar → "foo bar"
        if name.startswith("_parse__"):
            return name[8:].replace("_", " ")
        if name.startswith("parse_"):
            return name[6:].replace("_", " ")
    return None


@dataclass(frozen=True)
class OptionalPart(t.Generic[T]):
    """Optional parser component - may or may not match."""

    part: TokenType | set[TokenType] | t.Callable[[Parser], T]


@dataclass(frozen=True)
class RequiredPart(t.Generic[T]):
    """Required parser component - must match."""

    part: TokenType | set[TokenType] | t.Callable[[Parser], T]


@dataclass(frozen=True)
class ListPart(t.Generic[T]):
    """List of items with separator. min_items: 0=optional, 1+=required."""

    part: TokenType | set[TokenType] | t.Callable[[Parser], T]
    separator: TokenType | set[TokenType] | None
    min_items: int = 1
    allow_trailing_separator: bool = False


class Parser:
    """
    Recursive descent parser for GraphGlot.

    Processes token streams into AST expressions using grammar rules defined in _parse_* methods.
    Supports backtracking, error recovery, and multi-statement parsing.
    """

    PARSERS: t.ClassVar[dict[ParserKey, t.Callable[[Parser], t.Any]]] = get_registry()
    FUNCTIONS: t.ClassVar[dict[str, type]] = {}  # dialect overrides: name → Func subclass

    def __init__(
        self,
        error_level: ErrorLevel | None = None,
        error_message_context: int = 100,
        max_errors: int = 3,
        dialect: DialectType = None,
    ):
        from graphglot.dialect.base import Dialect

        self.error_level = error_level or ErrorLevel.IMMEDIATE
        self.error_message_context = error_message_context
        self.max_errors = max_errors
        self.dialect = Dialect.get_or_raise(dialect)
        self.reset()

    def reset(self):
        """Reset parser state for new parsing operation."""
        self.query = ""
        self.errors = []
        self._tokens = []
        self._index = 0
        self._curr = None
        self._next = None
        self._prev = None
        self._prev_comments = None
        self._furthest_error: ParseError | None = None
        self._furthest_index: int = -1

    def raise_error(self, message: str, token: Token | None = None) -> None:
        """Record or raise parsing error based on error_level."""
        token = token or self._curr or self._prev or Token(TokenType.EOF, "")

        error = _LazyParseError(
            message,
            tok_line=token.line,
            tok_col=token.col,
            tok_start=token.start,
            tok_end=token.end + 1,
            query=self.query,
            ctx_size=self.error_message_context,
        )

        # Track the deepest error for better diagnostics.
        # Use >= so the latest error at the deepest position wins — later
        # parse alternatives produce more specific error messages.
        error_index = self._index
        if error_index >= self._furthest_index:
            self._furthest_index = error_index
            self._furthest_error = error

        if self.error_level == ErrorLevel.IMMEDIATE:
            raise error
        self.errors.append(error)

    def check_errors(self) -> None:
        """Process accumulated errors based on error_level."""
        if self.error_level == ErrorLevel.WARN:
            for error in self.errors:
                logger.error(str(error))
        elif self.error_level == ErrorLevel.RAISE and self.errors:
            raise ParseError(
                message=concat_messages(self.errors, self.max_errors),
                errors=merge_errors(self.errors),
            )

    def parse(
        self, raw_tokens: list[Token], query: str | None = None, old_parsers: bool = True
    ) -> list[ast.Expression | None]:
        """Parse tokens into AST expressions."""
        return self._parse(self.PARSERS[ast.GqlProgram], raw_tokens, query)

    # Minimum recursion limit for the parser.  Each nesting level in deeply
    # nested expressions (e.g., list literals) costs ~15-20 stack frames after
    # fast-path optimizations.  Python's default of 1000 is too low for queries
    # with 20+ levels of nesting; 3000 comfortably handles ~150 levels.
    _MIN_RECURSION_LIMIT = 5000

    def _parse(
        self,
        parse_method: t.Callable[[Parser], ast.Expression | None],
        raw_tokens: list[Token],
        query: str | None = None,
    ) -> list[ast.Expression | None]:
        """Internal parse implementation with chunk handling."""
        self.reset()
        self.query = query or ""

        old_limit = sys.getrecursionlimit()
        if old_limit < self._MIN_RECURSION_LIMIT:
            sys.setrecursionlimit(self._MIN_RECURSION_LIMIT)

        try:
            return self._parse_chunks(parse_method, raw_tokens)
        except _LazyParseError as e:
            raise ParseError(str(e), e.errors) from None
        finally:
            sys.setrecursionlimit(old_limit)

    def _parse_chunks(
        self,
        parse_method: t.Callable[[Parser], ast.Expression | None],
        raw_tokens: list[Token],
    ) -> list[ast.Expression | None]:
        """Parse token chunks into AST expressions."""
        # Split tokens by semicolons for multi-statement support
        chunks = self._chunk_tokens(raw_tokens)
        expressions = []

        for tokens in chunks:
            self._index = -1
            self._tokens = tokens
            self._advance()

            result = parse_method(self)
            if isinstance(result, ListPart):
                result = self._parse_list_part(result)

            # Validate feature requirements after expression(s) are created
            if result is not None:
                from graphglot.ast.validation import validate_expression_features

                if isinstance(result, ast.Expression):
                    validate_expression_features(result, self.dialect, context="parsing")
                elif isinstance(result, list):
                    for expr in result:
                        if isinstance(expr, ast.Expression):
                            validate_expression_features(expr, self.dialect, context="parsing")

            expressions.append(result)

            if self._index < len(self._tokens):
                if self._furthest_error and self._furthest_index > self._index:
                    raise self._furthest_error
                self.raise_error("Unexpected token")
            self.check_errors()

        return expressions

    def _chunk_tokens(self, raw_tokens: list[Token]) -> list[list[Token]]:
        """Split tokens into chunks separated by semicolons."""
        chunks: list[list[Token]] = [[]]
        for i, token in enumerate(raw_tokens):
            if token.token_type == TokenType.SEMICOLON:
                if token.comments:
                    chunks.append([token])
                if i < len(raw_tokens) - 1:
                    chunks.append([])
            else:
                chunks[-1].append(token)
        return chunks

    def _advance(self, times: int = 1) -> None:
        """Advance parser position in token stream."""
        self._index += times
        self._curr = seq_get(self._tokens, self._index)
        self._next = seq_get(self._tokens, self._index + 1)
        self._prev = self._tokens[self._index - 1] if self._index > 0 else None
        self._prev_comments = self._prev.comments if self._prev else None

    def _retreat(self, index: int) -> None:
        """Move to specific position in token stream."""
        if index != self._index:
            self._advance(index - self._index)

    def _peek_at(self, offset: int) -> Token | None:
        """Peek at token at current position + offset without advancing."""
        idx = self._index + offset
        if 0 <= idx < len(self._tokens):
            return self._tokens[idx]
        return None

    def _match(self, token_type: TokenType | set[TokenType]) -> bool:
        """Check if current token(s) match type(s) or sequence."""
        if isinstance(token_type, set):
            for item in token_type:
                if self._curr and self._curr.token_type == item:
                    return True
            return False
        return token_matches(self._curr, token_type)

    def _match_next(self, token_type: TokenType | set[TokenType]) -> bool:
        """Check if next token(s) match type(s) or sequence."""
        if isinstance(token_type, set):
            for item in token_type:
                if self._next and self._next.token_type == item:
                    return True
            return False
        return token_matches(self._next, token_type)

    def _expect(self, token_type: TokenType | set[TokenType]) -> Token | list[Token]:
        """Assert current token(s) match expected and advance."""

        if isinstance(token_type, set):
            for item in token_type:
                if self._curr and self._curr.token_type == item:
                    matched = self._curr
                    self._advance()
                    return matched
            # No match - raise error with expected types
            expected = ", ".join(item.name for item in token_type)
            self.raise_error(f"Expected one of [{expected}]")
            raise ParseError(f"Expected one of [{expected}]")

        # Single TokenType
        if not isinstance(token_type, TokenType):
            raise TypeError(f"Expected TokenType, got {type(token_type)}")
        if not self._match(token_type):
            self.raise_error(f"Expected {token_type.name}")
            raise ParseError(f"Expected {token_type.name}")
        matched = self._curr
        self._advance()
        return matched

    def get_parser(self, expr_type: ParserKey) -> t.Callable[[Parser], t.Any]:
        """Get registered parser for expression type."""
        parser = self.PARSERS.get(expr_type)
        if not parser:
            raise NotImplementedError(
                f"No parser registered for {expr_type}. "
                f"Use @parses({getattr(expr_type, '__name__', str(expr_type))}) to register one."
            )
        return parser

    def try_parse(
        self,
        parser: t.Callable[[Parser], ast.Expression],
        retreat: bool = False,
    ) -> ast.Expression | None:
        """Attempt parse with automatic backtracking on failure."""
        if self._curr is None:
            return None

        index = self._index
        error_level = self.error_level
        result = None

        self.error_level = ErrorLevel.IMMEDIATE
        try:
            result = parser(self)
        except ParseError:
            pass
        finally:
            if not result or retreat:
                self._retreat(index)
            self.error_level = error_level

        return result

    def try_parse_any(
        self, *parsers: t.Callable[[Parser], ast.Expression]
    ) -> ast.Expression | None:
        """Try parsers in order, return first match."""
        if self._curr is None:
            return None
        for parser in parsers:
            if node := self.try_parse(parser):
                return node
        return None

    def parse_one_of(
        self,
        *parsers: t.Callable[[Parser], ast.Expression],
        message: str | None = None,
    ) -> ast.Expression:
        """Require one parser to match, raise error if none do."""
        start_index = self._index
        if node := self.try_parse_any(*parsers):
            return node

        self._retreat(start_index)
        if not message:
            descriptions = [d for p in parsers if (d := _parser_description(p))]
            if descriptions:
                message = f"Expected {' or '.join(descriptions)}"
            else:
                message = "Unexpected token"
        self.raise_error(message)
        raise ParseError(message)

    def _parse_list_part(self, list_part: ListPart[t.Any]) -> list[t.Any]:
        """Parse list of items with optional separator."""
        items: list[t.Any] = []

        # Parse first element
        if (first := self._try_list_elem(list_part.part)) is None:
            if list_part.min_items > 0:
                # Require at least one element
                self.raise_error("Expected at least one list element")
            return items
        items.append(first)

        # Parse remaining elements
        if list_part.separator is None:
            # No separator: parse until can't
            while (elem := self._try_list_elem(list_part.part)) is not None:
                items.append(elem)
        else:
            # With separator
            while self._match(list_part.separator):
                self._advance()
                if (elem := self._try_list_elem(list_part.part)) is None:
                    if list_part.allow_trailing_separator:
                        break
                    sep = self._prev  # the separator token we just consumed
                    self.raise_error(
                        f"Unexpected trailing '{sep.text}'"
                        if sep
                        else "Expected element after separator"
                    )
                items.append(elem)

        # Enforce minimum number of items for any min_items >= 0
        if len(items) < list_part.min_items:
            self.raise_error(f"Expected at least {list_part.min_items} list elements")

        return items

    def _try_list_elem(self, inner: t.Any) -> t.Any:
        """Try to parse single list element."""

        if isinstance(inner, TokenType):
            if self._match(inner):
                tok = self._curr
                self._advance()
                return tok
            return None

        if isinstance(inner, set):
            if not inner:
                raise ValueError("Empty set not allowed in ListPart")
            sample = next(iter(inner))
            if callable(sample):
                return self.try_parse_any(*inner)
            if token_matches(self._curr, inner):
                tok = self._curr
                self._advance()
                return tok
            return None

        if callable(inner):
            return self.try_parse(inner)

        raise TypeError(f"Unsupported ListPart inner: {inner!r}")

    def _maybe_list(self, v: t.Any) -> t.Any:
        """Convert ListPart to list if needed, otherwise return as-is."""
        return self._parse_list_part(v) if isinstance(v, ListPart) else v

    def seq(
        self,
        *parts: t.Any,
        skip_opt_if_next_token_matches: bool = True,
    ) -> list[t.Any]:
        """
        Parse sequence atomically. Required parts must all match or entire sequence fails.
        Optional parts contribute None if they don't match.
        """
        start_index = self._index
        original_level = self.error_level
        self.error_level = ErrorLevel.IMMEDIATE
        results = []

        try:
            for i, part in enumerate(parts):
                results.append(self._parse_part(part, i, parts, skip_opt_if_next_token_matches))
            return results
        except ParseError:
            self._retreat(start_index)
            raise
        finally:
            self.error_level = original_level

    def _parse_part(self, part: t.Any, idx: int, all_parts: tuple, skip_opt: bool) -> t.Any:
        """Parse single part in sequence."""

        # TokenType
        if isinstance(part, TokenType):
            return self._expect(part)

        # Sequence of parsers
        if isinstance(part, t.Sequence) and part and callable(part[0]):
            return self._maybe_list(self.parse_one_of(*part))

        # Set of tokens or parsers
        if isinstance(part, set):
            if not part:
                raise ValueError("Empty set not allowed")
            sample = next(iter(part))
            if callable(sample):
                return self._maybe_list(self.parse_one_of(*part))
            return self._expect(part)

        # OptionalPart
        if isinstance(part, OptionalPart):
            return self._parse_optional(part, idx, all_parts, skip_opt)

        # RequiredPart
        if isinstance(part, RequiredPart):
            return self._parse_required(part)

        # ListPart
        if isinstance(part, ListPart):
            return self._parse_list_part(part)

        # Callable parser
        if callable(part):
            return self._maybe_list(part(self))

        raise TypeError(f"Unsupported part {part!r}")

    def _parse_optional(
        self, part: OptionalPart, idx: int, all_parts: tuple, skip_opt: bool
    ) -> t.Any:
        """Parse optional part."""
        # Check if should skip based on next token
        if skip_opt:
            next_tok = self._get_next_token_type(idx, all_parts)
            if next_tok and token_matches(self._curr, next_tok):
                return None

        inner = part.part

        if isinstance(inner, TokenType):
            if self._match(inner):
                tok = self._curr
                self._advance()
                return tok
            return None

        if isinstance(inner, set):
            if not inner:
                raise ValueError("Empty set not allowed in OptionalPart")
            sample = next(iter(inner))
            if callable(sample):
                parser_set = t.cast(set[t.Callable[[Parser], ast.Expression]], inner)
                return self._maybe_list(self.try_parse_any(*parser_set))
            if token_matches(self._curr, inner):
                tok = self._curr
                self._advance()
                return tok
            return None

        if callable(inner):
            return self._maybe_list(self.try_parse(inner))

        raise TypeError(f"Unsupported OptionalPart inner: {inner!r}")

    def _parse_required(self, part: RequiredPart) -> t.Any:
        """Parse required part."""
        inner = part.part

        if isinstance(inner, TokenType):
            return self._expect(inner)

        if isinstance(inner, set):
            if not inner:
                raise ValueError("Empty set not allowed in RequiredPart")
            sample = next(iter(inner))
            if callable(sample):
                parser_set = t.cast(set[t.Callable[[Parser], ast.Expression]], inner)
                return self._maybe_list(self.parse_one_of(*parser_set))
            return self._expect(inner)

        if callable(inner):
            return self._maybe_list(inner(self))

        raise TypeError(f"Unsupported RequiredPart inner: {inner!r}")

    def _get_next_token_type(self, idx: int, parts: tuple) -> TokenType | set[TokenType] | None:
        """Get token type of next part if it's a token."""
        if idx + 1 >= len(parts):
            return None
        next_part = parts[idx + 1]
        if isinstance(next_part, TokenType):
            return next_part
        if isinstance(next_part, set) and next_part:
            sample = next(iter(next_part))
            if not callable(sample):
                return next_part
        return None

    def try_seq(self, *parts: t.Any) -> list[ast.Expression | Token | None] | None:
        """Try sequence, return None on failure."""
        start_index = self._index
        try:
            return self.seq(*parts)
        except ParseError:
            self._retreat(start_index)
            return None

    def opt(self, part: t.Any) -> OptionalPart:
        """Create optional part."""
        return OptionalPart(part)

    def req(self, part: t.Any) -> RequiredPart:
        """Create required part."""
        return RequiredPart(part)

    def list_(self, part: t.Any, separator: t.Any, min_items: int = 1) -> ListPart:
        """Create list part."""
        return ListPart(part, separator, min_items)
