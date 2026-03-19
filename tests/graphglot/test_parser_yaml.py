# import pathlib
# import unittest

# import yaml

# from graphglot import ast
# from graphglot.error import ParseError, ParseNotImplementedError
# from graphglot.lexer import Lexer
# from graphglot.parser import Parser  # adjust path if needed

# ERROR_TYPES = {
#     "ParseError": ParseError,
#     "ParseNotImplementedError": ParseNotImplementedError,
# }


# class TestParserFromYaml(unittest.TestCase):
#     @classmethod
#     def setUpClass(cls):
#         base = pathlib.Path(__file__).parent
#         config_path = base / "parser_tests.yaml"
#         with config_path.open("r", encoding="utf-8") as f:
#             cls.config = yaml.safe_load(f)

#         cls.default_dialect_name = cls.config.get("defaults", {}).get("dialect")

#     def test_cases(self):
#         for case in self.config.get("tests", []):
#             name = case.get("name")
#             query = case["query"]
#             variants = case.get("variants", [])

#             if not variants:
#                 self.fail(f"Test case {name!r} has no variants defined")

#             for variant in variants:
#                 dialect_name = variant.get("dialect", self.default_dialect_name)
#                 label = f"{name} [dialect={dialect_name}]"
#                 with self.subTest(case=label):
#                     self._run_variant(query, variant, dialect_name)

#     def _run_variant(self, query: str, variant: dict, dialect_name: str) -> None:
#         mode = variant.get("mode", "parse")
#         root_name = variant.get("root")
#         expect = variant["expect"]

#         tokens = Lexer().tokenize(query)

#         # Resolve dialect: you can pass the name directly if Dialect.get_or_raise
#         # accepts it; otherwise adapt this.
#         parser = Parser(dialect=dialect_name)

#         def run():
#             if mode == "parse":
#                 return parser.parse(raw_tokens=tokens, query=query)
#             elif mode == "direct":
#                 if not root_name:
#                     raise RuntimeError("mode 'direct' requires a 'root' field")
#                 root_cls = getattr(ast, root_name)
#                 parse_method = Parser.PARSERS[root_cls]
#                 return parser._parse(
#                     raw_tokens=tokens,
#                     query=query,
#                     parse_method=parse_method,
#                 )
#             else:
#                 raise RuntimeError(f"Unknown mode: {mode}")

#         kind = expect["kind"]

#         if kind == "error":
#             err_type_name = expect["error_type"]
#             exc_type = ERROR_TYPES[err_type_name]
#             with self.assertRaises(exc_type):
#                 run()
#             return

#         if kind != "success":
#             raise RuntimeError(f"Unknown expect.kind: {kind}")

#         # Success: compare leaves
#         result = run()
#         expr = result[0]
#         actual_leaves = expr.leaf_list()

#         expected_leaves_cfg = expect.get("leaves", [])
#         expected_leaves = [self._build_ast_leaf(spec) for spec in expected_leaves_cfg]

#         self.assertEqual(
#             actual_leaves,
#             expected_leaves,
#             f"Leaf list mismatch for dialect {dialect_name!r}",
#         )

#     def _build_ast_leaf(self, spec: dict):
#         type_name = spec["type"]
#         params = spec.get("params", {}) or {}
#         cls = getattr(ast, type_name)
#         return cls(**params)
