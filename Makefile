
# Colors
GREEN=\033[0;32m
NC=\033[0m
PURPLE=\033[0;35m

# Emojis
CHECK_MARK=✅
INFO_MARK=ℹ️
ROCKET=🚀
WAVING_HAND=👋
BUILDING=🏗️

# Help
help:
	@echo "\n${WAVING_HAND} Welcome to the GraphGlot project!${NC}\n"
	@echo "${ROCKET} Here are some things you can do:\n"
	@echo "${PURPLE}${INFO_MARK}  test:             ${NC} Run tests"
	@echo "${PURPLE}${INFO_MARK}  test-cov:         ${NC} Run tests with coverage"
	@echo "${PURPLE}${INFO_MARK}  neo4j:            ${NC} Run Neo4j integration tests"
	@echo "${PURPLE}${INFO_MARK}  type:             ${NC} Run static type checks"
	@echo "${PURPLE}${INFO_MARK}  pre:              ${NC} Run formatter"
	@echo "${PURPLE}${INFO_MARK}  docs-serve:       ${NC} Serve docs locally"
	@echo "${PURPLE}${INFO_MARK}  docs-build:       ${NC} Build docs (strict)"
	@echo "${PURPLE}${INFO_MARK}  version-check:    ${NC} Check version consistency"
	@echo "${PURPLE}${INFO_MARK}  version-sync:     ${NC} Sync uv.lock with pyproject.toml"
	@echo "${PURPLE}${INFO_MARK}  audit:            ${NC} Dependency vulnerability scan"
	@echo "${PURPLE}${INFO_MARK}  tck:              ${NC} openCypher TCK conformance tests"
	@echo "${PURPLE}${INFO_MARK}  fuzz:             ${NC} Property-based parser fuzzing"
	@echo "${PURPLE}${INFO_MARK}  bnf-strip:        ${NC} Strip BNF definitions"
	@echo "${PURPLE}${INFO_MARK}  bnf-restore:      ${NC} Restore BNF definitions"
	@echo "${PURPLE}${INFO_MARK}  clean:            ${NC} Clean cache\n"

test:
	@echo "${GREEN}${BUILDING} Running unit tests...${NC}"
	pytest --durations=10 -m "not integration and not fuzz and not tck" tests/graphglot/
	@echo "${GREEN}${CHECK_MARK} Tests ran successfully!${NC}"

test-cov:
	@echo "${GREEN}${BUILDING} Running tests with coverage...${NC}"
	pytest --cov=graphglot --cov-report=term-missing -m "not integration and not fuzz and not tck" tests/graphglot/
	@echo "${GREEN}${CHECK_MARK} Tests with coverage ran successfully!${NC}"

neo4j:
	@echo "${GREEN}${BUILDING} Running Neo4j integration tests...${NC}"
	pytest -m integration tests/graphglot/integration/ -v
	@echo "${GREEN}${CHECK_MARK} Integration tests ran successfully!${NC}"

type:
	@echo "${GREEN}${BUILDING} Running static type checks...${NC}"
	uv run --extra dev mypy graphglot
	@echo "${GREEN}${CHECK_MARK} Type checks ran successfully!${NC}"

pre:
	@echo "${GREEN}${BUILDING} Formatting...${NC}"
	pre-commit run --all-files
	@echo "${GREEN}${CHECK_MARK} Formatting ran successfully!${NC}"

docs-serve:
	@echo "${GREEN}${BUILDING} Serving docs...${NC}"
	NO_MKDOCS_2_WARNING=1 uv run --extra docs mkdocs serve --dev-addr 0.0.0.0:8000

docs-build:
	@echo "${GREEN}${BUILDING} Building docs...${NC}"
	NO_MKDOCS_2_WARNING=1 uv run --extra docs mkdocs build --strict
	@echo "${GREEN}${CHECK_MARK} Docs built successfully!${NC}"

version-check:
	@echo "${GREEN}${BUILDING} Checking version consistency...${NC}"
	python scripts/check_version_consistency.py $(if $(EXPECTED),--expected $(EXPECTED),)
	@echo "${GREEN}${CHECK_MARK} Version check passed!${NC}"

version-sync:
	@echo "${GREEN}${BUILDING} Syncing uv.lock...${NC}"
	uv lock
	@echo "${GREEN}${CHECK_MARK} uv.lock synced!${NC}"

audit:
	@echo "${GREEN}${BUILDING} Running dependency audit...${NC}"
	osv-scanner scan --lockfile uv.lock
	@echo "${GREEN}${CHECK_MARK} Dependency audit passed!${NC}"

tck:
	@echo "${GREEN}${BUILDING} Running TCK conformance tests...${NC}"
	pytest -m tck tests/graphglot/tck/ -v --tb=short
	@echo "${GREEN}${CHECK_MARK} TCK tests passed!${NC}"

fuzz:
	@echo "${GREEN}${BUILDING} Running fuzz tests...${NC}"
	pytest -m fuzz tests/graphglot/ -v --timeout=120
	@echo "${GREEN}${CHECK_MARK} Fuzz tests passed!${NC}"

bnf-strip:
	@echo "${GREEN}${BUILDING} Stripping BNF definitions...${NC}"
	python scripts/bnf.py strip
	@echo "${GREEN}${CHECK_MARK} BNF stripped → bnf.json${NC}"

bnf-restore:
	@echo "${GREEN}${BUILDING} Restoring BNF definitions...${NC}"
	python scripts/bnf.py restore
	@echo "${GREEN}${CHECK_MARK} BNF restored!${NC}"

clean:
	@echo "${GREEN}${BUILDING} Cleaning cache...${NC}"
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .hypothesis
	rm -rf site
	find . -type d -name __pycache__ -print -exec rm -r {} +
	@echo "${GREEN}${CHECK_MARK} Cache cleaned!${NC}"
