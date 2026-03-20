# CHANGELOG

<!-- version list -->

## v0.1.3 (2026-03-20)

### Bug Fixes

- **ci**: Use semantic-release action to trigger PyPI publish
  ([`f063bf5`](https://github.com/averdeny/graphglot/commit/f063bf5a12d3614b8e6290c5fa9b9587086c5df8))


## v0.1.2 (2026-03-20)

### Bug Fixes

- Resolve PathValueConcatenation parser by using list_ with min_items=2
  ([`3b9082e`](https://github.com/averdeny/graphglot/commit/3b9082e9cdcc6433656ac8b1cafa7fb8abda8d48))

### Chores

- Remove .devcontainer from version control
  ([`be1210f`](https://github.com/averdeny/graphglot/commit/be1210f913f7e033af369798c29408953db90e92))

### Continuous Integration

- Add GitHub Pages docs deployment
  ([`0dce280`](https://github.com/averdeny/graphglot/commit/0dce28060da8a7982e51b52ea63a105ac8dd0a92))

- Clarify workflow display names and fix README badge
  ([`fb0bc6f`](https://github.com/averdeny/graphglot/commit/fb0bc6f8c517b770f4574a5603ac03ec9ab38b7d))

- Configure PyPI trusted publishing
  ([`d71a675`](https://github.com/averdeny/graphglot/commit/d71a67595bc2a99d16ac5a30749cae41e7e4927e))

- Rename build-test-lint.yml to test-lint.yml
  ([`0edc825`](https://github.com/averdeny/graphglot/commit/0edc8256d5071bf1dcee1d6ec44870ff453dd5cf))

- Rename workflow to test-lint.yml and fix badge and display name
  ([`f4700ec`](https://github.com/averdeny/graphglot/commit/f4700ec4149d229b4fa5db93f7ba4d73a55f9795))

### Refactoring

- Remove pydantic dependency from AST base class
  ([`40a4362`](https://github.com/averdeny/graphglot/commit/40a4362e881f37c7dd939794e9145c70e92a2d41))


## v0.1.1 (2026-03-19)

### Bug Fixes

- **tck**: Increase parse test timeout to 10s for CI runners
  ([`d4dda2c`](https://github.com/averdeny/graphglot/commit/d4dda2c2f6fad252547d2b30abaad11d9770e986))

### Continuous Integration

- Add TCK conformance tests to CI pipeline
  ([`1a36510`](https://github.com/averdeny/graphglot/commit/1a365103bd9f0090cd8a6cdf7ecb4e3d4e8bfd71))
