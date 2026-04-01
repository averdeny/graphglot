# CHANGELOG

<!-- version list -->

## v0.8.3 (2026-04-01)

### Bug Fixes

- Resolve 26 TCK roundtrip xfails by allowing node rebinding in Cypher CREATE/MERGE
  ([`2bfa8eb`](https://github.com/averdeny/graphglot/commit/2bfa8eb5f7e2a18c6c1040491ef96410be49da98))


## v0.8.2 (2026-04-01)

### Bug Fixes

- Resolve 15 TCK roundtrip xfails via feature declarations
  ([`8feea74`](https://github.com/averdeny/graphglot/commit/8feea7413c8f1a72a8aa2ff5e0f9cad4a8835ba5))

- Resolve 28 TCK roundtrip xfails via feature gating and scope fix
  ([`e32731c`](https://github.com/averdeny/graphglot/commit/e32731ca347c17ef1d569231ebc2b5e21e2b3f02))

- Transpile Cypher list concatenation (+) to GQL (||)
  ([`71a354c`](https://github.com/averdeny/graphglot/commit/71a354c6f14e2194e0d566a0205b2eb106d0afaf))


## v0.8.1 (2026-03-31)

### Bug Fixes

- Resolve WITH...WHERE scope loss in with_to_next transformation
  ([`4624c23`](https://github.com/averdeny/graphglot/commit/4624c23d9988c0d3ee8b6d4d7b16b00093ef7484))


## v0.8.0 (2026-03-31)

### Features

- Add CypherPredicateComparison base generator and fix list predicate formatting
  ([`35d36e1`](https://github.com/averdeny/graphglot/commit/35d36e1d63133bf22974b3bb7430f642e20e5a6c))

- Add GQL generator for Cypher CreateClause → INSERT
  ([`3495c4e`](https://github.com/averdeny/graphglot/commit/3495c4e4ae178184381cf1e86f5324b450305b4d))


## v0.7.0 (2026-03-31)

### Features

- Add base generators for LocaldatetimeFunction, LocaltimeFunction, DurationFunction
  ([`a2e1eb7`](https://github.com/averdeny/graphglot/commit/a2e1eb7c62fb8f6d83d308a3229fa738377f73c4))

- Inject implicit DIFFERENT EDGES default match mode
  ([`708eff2`](https://github.com/averdeny/graphglot/commit/708eff22b0e043aa2262afa9757a2cbd7f8c3a7b))


## v0.6.1 (2026-03-29)

### Bug Fixes

- Avoid stale scope validator cache hits
  ([`ffb504a`](https://github.com/averdeny/graphglot/commit/ffb504ab7fc739e704f7fac2f1e6c79c15c9bdd9))

- Wrap NotImplementedError from generate() as FeatureError in transpile()
  ([`3fd608c`](https://github.com/averdeny/graphglot/commit/3fd608cf9b51cb0114dfefda5f8870240fa661f5))

### Refactoring

- Move Cypher expression rewrites from transformations to generators
  ([`c4ee222`](https://github.com/averdeny/graphglot/commit/c4ee22237655a148253bbb361fd0e1caa8f87558))

### Testing

- Add EXISTS subquery scope test for synthetic nodes from with_to_next
  ([`ecff51d`](https://github.com/averdeny/graphglot/commit/ecff51d175f8967a8570522bd886977f9362bbc7))


## v0.6.0 (2026-03-28)

### Bug Fixes

- Use pruned DFS in extract_variable_references to fix synthetic subquery scoping
  ([`6fb7d32`](https://github.com/averdeny/graphglot/commit/6fb7d328e171bbdc831cced0ebb1b5e5cdf3606d))

### Documentation

- Remove gql_features.md and tck.md
  ([`bea2eae`](https://github.com/averdeny/graphglot/commit/bea2eae43c09d17ac1770f60a0d54b634cac9bc9))

### Features

- Add list predicate rewrites and split transformations into composable functions
  ([`cc7bd9f`](https://github.com/averdeny/graphglot/commit/cc7bd9fcc7a5f0318883fa901da7c1bad34b681a))

- Add rewrite_cypher_predicates transformation for Cypher→GQL transpilation
  ([`999419f`](https://github.com/averdeny/graphglot/commit/999419f9c0f729ab6ed96d8a397f75d796365667))

- Parse temporal casts and duration.between into GQL AST at parse time
  ([`a11b440`](https://github.com/averdeny/graphglot/commit/a11b4403451dc5f4ca1bfb051ad3e029b17e5677))


## v0.5.0 (2026-03-25)

### Features

- Add GG22/GG23 analysis rules for key label set inference and optional key label sets
  ([`149b8bd`](https://github.com/averdeny/graphglot/commit/149b8bd634631526c75821eeb497c714374521b1))


## v0.4.0 (2026-03-24)

### Features

- Add GP14/GP15 analysis rules for procedure argument type gating
  ([`5295893`](https://github.com/averdeny/graphglot/commit/5295893fb5a3b6ca986720b0c0b3e3aac08ee9e8))

### Refactoring

- Make find_all/find_first generic and remove redundant t.cast calls
  ([`cab28c5`](https://github.com/averdeny/graphglot/commit/cab28c52c8b4010962222cefcd2c6285ec471dc2))

- Use typed Feature objects in @analysis_rule decorator
  ([`8280faa`](https://github.com/averdeny/graphglot/commit/8280faacd733cff276cda6da8ded788b4ee35a3e))


## v0.3.1 (2026-03-23)

### Bug Fixes

- Improve invalid-delete-target diagnostic message
  ([`761f3ae`](https://github.com/averdeny/graphglot/commit/761f3ae75cba896e667b2b4dbe932caab613680b))

- Remove redundant invalid-delete-target structural rule
  ([`1fa11be`](https://github.com/averdeny/graphglot/commit/1fa11bea0b5763bbb95a19c607994f606aa32189))

- Upgrade CVE to BVE when predicate/boolean token follows in ValueExpression
  ([`7621a9a`](https://github.com/averdeny/graphglot/commit/7621a9a1ac40fc7ef88ddcc95d16edca16bf8322))

### Documentation

- Correct GD03/GD04 feature descriptions and examples
  ([`76bc709`](https://github.com/averdeny/graphglot/commit/76bc709f1af62cfbdcc22241c7e476b28c53fb0a))


## v0.3.0 (2026-03-23)

### Bug Fixes

- Reject non-arithmetic/non-concat operands in ambiguous type resolution
  ([`5190edb`](https://github.com/averdeny/graphglot/commit/5190edb2859832999d8f8dfade662c332f754338))

### Features

- Add type-mismatch structural rule for concat and arithmetic operands
  ([`a204d26`](https://github.com/averdeny/graphglot/commit/a204d26cbd1090c63023828d2437e21f6ae115a6))


## v0.2.0 (2026-03-20)

### Bug Fixes

- Include temporal types in unknown arithmetic union to prevent false-positive GA04
  ([`bed5cde`](https://github.com/averdeny/graphglot/commit/bed5cdea662b86c13baeb79a859310984d81d96f))

- Prevent temporal type propagation through multiplicative arithmetic
  ([`8557571`](https://github.com/averdeny/graphglot/commit/8557571543148f99237615acb5628b23b3292dfb))

- Propagate temporal types through ambiguous arithmetic expressions
  ([`b0f7981`](https://github.com/averdeny/graphglot/commit/b0f79812d383a257d48c55d54431e5c9e17017d4))

### Features

- Transform AmbiguousValueExpression to concrete GQL types
  ([`5684ebf`](https://github.com/averdeny/graphglot/commit/5684ebf894e0e2bb8a1aabcc8ab9460fb03dbcdd))


## v0.1.5 (2026-03-20)

### Bug Fixes

- Add missing generators for AbsoluteValueExpression and DurationAbsoluteValueFunction
  ([`e9b2f94`](https://github.com/averdeny/graphglot/commit/e9b2f948160c4f3d90f8db37ef5df7c9ffd8c229))

- Handle BYTE_STRING in concatenation type resolution rule
  ([`7838142`](https://github.com/averdeny/graphglot/commit/7838142e013b2b83ef7c49e3e9ceceecab294a16))

- Propagate type through BindingVariableReference to parent nodes
  ([`485c863`](https://github.com/averdeny/graphglot/commit/485c8633325a094c6905a3a792c0c9a9fadabae2))


## v0.1.4 (2026-03-20)

### Bug Fixes

- **ci**: Inline publish job to avoid reusable workflow OIDC issues
  ([`0e33fa9`](https://github.com/averdeny/graphglot/commit/0e33fa9df618288dc46fdeb49991d058af0e0aff))


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
