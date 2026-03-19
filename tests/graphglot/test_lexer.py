import unittest

from graphglot.error import TokenError
from graphglot.lexer import Lexer, TokenType


class TestLexer(unittest.TestCase):
    def test_token_attributes(self):
        """Test that tokens have the correct attributes and position tracking."""

        query = "MATCH (n) RETURN n"
        tokens = Lexer().tokenize(query)

        # Test first token (MATCH)
        self.assertEqual(tokens[0].token_type, TokenType.MATCH)
        self.assertEqual(tokens[0].text, "MATCH")
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[0].col, 6)  # "MATCH" is 5 chars, so column is 6 after the token
        self.assertEqual(tokens[0].start, 0)
        self.assertEqual(tokens[0].end, 4)  # "MATCH" is 5 chars, so end is 4 (0-based)

    def test_simple_query(self):
        """Test basic tokenization of a simple query."""

        query = "MATCH (n) RETURN n"
        tokens = Lexer().tokenize(query)

        expected_token_types = {
            TokenType.MATCH,
            TokenType.VAR,
            TokenType.RETURN,
            TokenType.LEFT_PAREN,
            TokenType.RIGHT_PAREN,
        }

        self.assertEqual(len(tokens), 6)
        self.assertTrue(all(token.token_type in expected_token_types for token in tokens))

    def test_string_literals(self):
        """Test handling of string literals with different quote types."""

        query = "MATCH (n) WHERE n.name = 'Alice' AND n.title = \"Manager\""
        tokens = Lexer().tokenize(query)

        # Find string literals
        string_tokens = [t for t in tokens if t.token_type == TokenType.STRING]
        self.assertEqual(len(string_tokens), 2)
        self.assertEqual(string_tokens[0].text, "Alice")
        self.assertEqual(string_tokens[1].text, "Manager")

    def test_comments(self):
        """Test handling of single-line and multi-line comments."""

        query = """
        MATCH (n) // This is a comment
        /* This is a
           multi-line comment */
        RETURN n
        """
        tokens = Lexer().tokenize(query)

        return_token = next(t for t in tokens if t.token_type == TokenType.RETURN)
        self.assertTrue(len(return_token.comments) > 0)

    def test_numbers(self):
        """Test handling of integer and floating point numbers."""

        query = "MATCH (n) WHERE n.age = 42 AND n.score = 3.14"
        tokens = Lexer().tokenize(query)

        number_tokens = [t for t in tokens if t.token_type == TokenType.NUMBER]
        self.assertEqual(len(number_tokens), 2)
        self.assertEqual(number_tokens[0].text, "42")
        self.assertEqual(number_tokens[1].text, "3.14")

    def test_operators(self):
        """Test handling of various operators."""

        query = "MATCH (n) WHERE n.age > 18 AND n.score <= 100 OR n.name <> 'Unknown'"
        tokens = Lexer().tokenize(query)

        operator_types = {
            TokenType.RIGHT_ANGLE_BRACKET,  # >
            TokenType.LESS_THAN_OR_EQUALS_OPERATOR,  # <=
            TokenType.NOT_EQUALS_OPERATOR,  # <>
            TokenType.AND,  # AND
            TokenType.OR,  # OR
        }

        operator_tokens = [t for t in tokens if t.token_type in operator_types]
        self.assertEqual(len(operator_tokens), 5)

    def test_node_pattern_with_property_map(self):
        """Test handling of node patterns with property maps."""

        query = "MATCH (n:Person {name: 'Alice', age: 30})"
        tokens = Lexer().tokenize(query)

        self.assertEqual(len(tokens), 15)

    def test_identifier_quotation(self):
        """Test handling of identifiers with special characters."""

        query = "MATCH (`user-name`) RETURN `user-name`"
        tokens = Lexer().tokenize(query)

        var_tokens = [t for t in tokens if t.token_type == TokenType.VAR]
        self.assertEqual(len(var_tokens), 2)
        self.assertEqual(var_tokens[0].text, "user-name")
        self.assertEqual(var_tokens[1].text, "user-name")

    def test_error_handling(self):
        """Test error handling for invalid input."""

        query = "MATCH (n) WHERE n.name = 'Unclosed string"

        with self.assertRaises(TokenError):
            Lexer().tokenize(query)

    def test_optional_match(self):
        """Test handling of OPTIONAL MATCH clause."""

        query = "OPTIONAL MATCH (n:Person) RETURN n"
        tokens = Lexer().tokenize(query)

        # Ensure two tokens OPTIONAL and MATCH are present
        optional_token = next(t for t in tokens if t.token_type == TokenType.OPTIONAL)
        match_token = next(t for t in tokens if t.token_type == TokenType.MATCH)
        self.assertIsNotNone(optional_token)
        self.assertIsNotNone(match_token)
        self.assertEqual(optional_token.text, "OPTIONAL")
        self.assertEqual(match_token.text, "MATCH")

    def test_union(self):
        """Test handling of UNION and UNION ALL clauses."""

        query = "MATCH (n) RETURN n UNION ALL MATCH (m) RETURN m UNION MATCH (o) RETURN o"
        tokens = Lexer().tokenize(query)

        union_token = next(t for t in tokens if t.token_type == TokenType.UNION)
        all_token = next(t for t in tokens if t.token_type == TokenType.ALL)

        self.assertIsNotNone(union_token)
        self.assertEqual(union_token.text, "UNION")
        self.assertIsNotNone(all_token)
        self.assertEqual(all_token.text, "ALL")

    def test_distinct(self):
        """Test handling of DISTINCT keyword in RETURN clause."""

        query = "MATCH (n) RETURN DISTINCT n"
        tokens = Lexer().tokenize(query)

        distinct_token = next(t for t in tokens if t.token_type == TokenType.DISTINCT)
        self.assertIsNotNone(distinct_token)
        self.assertEqual(distinct_token.text, "DISTINCT")

    def test_numbers_can_be_underscores_separated(self):
        """Test that numbers can be underscores separated."""

        query = "1_000"
        tokens = Lexer().tokenize(query)

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.NUMBER)
        self.assertEqual(tokens[0].text, "1_000")

    def test_decimals_can_be_underscores_separated(self):
        """Test that decimal numbers can be underscores separated."""

        query = "1_000.00"
        tokens = Lexer().tokenize(query)

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.NUMBER)
        self.assertEqual(tokens[0].text, "1_000.00")

    def test_numbers_cannot_be_underscores_separated_at_the_beginning(self):
        """Test that numbers cannot be underscores separated at the beginning."""

        query = "_123"
        tokens = Lexer().tokenize(query)

        self.assertEqual(len(tokens), 1)
        self.assertNotEqual(tokens[0].token_type, TokenType.NUMBER)

    def test_numbers_cannot_be_underscores_separated_at_the_end(self):
        """Test that numbers cannot be underscores separated at the end."""

        query = "123_"
        with self.assertRaises(TokenError):
            Lexer().tokenize(query)
