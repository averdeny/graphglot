# CLAUDE.md

GraphGlot is a Python library for parsing, validating, and transpiling graph query languages (Cypher/GQL) via a Lexer → Parser → AST pipeline.

## TDD

Write failing tests first, then implement. Red → Green → Refactor.

## Validation

```bash
make test      # unit tests (pytest tests/graphglot/)
make pre       # linter/formatter (ruff + pre-commit)
make type      # type checking
make neo4j     # integration tests
```

## Commits

Use Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `style:`, `chore:`.
