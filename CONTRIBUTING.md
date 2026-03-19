# Contributing to GraphGlot

GraphGlot is an open-source project and we welcome new contributors!

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

- **Bugs & small fixes** – Open a PR
- **New features & architecture changes** – Open a Github Issue
- **Questions** – Reach out to hello@graphglot.com

## Getting Started

Fork the repo, install dependencies (`pip install -e ".[dev]"` or `uv sync --extra dev`), and run `pre-commit install`. Python 3.11+ is required; Docker is only needed for integration tests (`make neo4j`).

Before opening a PR, make sure these pass locally:

```bash
make test      # unit tests
make type      # type checking
make pre       # linter/formatter
```

## License

By contributing, you agree that your contributions will be licensed under the [LICENSE](./LICENSE).
