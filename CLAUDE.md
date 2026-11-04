# CLAUDE.md

Generic MCP server over streamable HTTP (Python, official `mcp` SDK, FastMCP) with three mock
tools. Built with Clean Architecture, OpenTelemetry tracing and structured logging.
This file is self-contained: it holds both the general standards and the project specifics.

## Commands

```bash
make install     # pip install -e ".[dev]"
make run         # python main.py (reads .env)
make test        # pytest (single test: python -m pytest tests/path/test_x.py::test_name)
make lint        # ruff check + ruff format --check
make format      # ruff fix + format
make typecheck   # pyright
make check       # lint + typecheck + test (same as CI)
make docker-up   # docker compose up --build (server + Jaeger)
```

Run `make check` before declaring any task done, and report what you could not verify
(for example Docker builds or external services).

## Working style
- Make the smallest change that solves the task; do not refactor unrelated code.
- Read the existing code and follow its conventions before adding new ones.
- If a request is ambiguous and a wrong guess is costly, ask one short question first.
- Do not commit or push unless asked. Never commit generated files, caches or build output.
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`),
  imperative mood, subject under 72 characters.
- Reply in English. Code, comments, docstrings, identifiers, tests and commit text are English.

## Architecture
Clean Architecture; dependencies point inwards only. `tests/architecture/test_dependency_rule.py`
enforces it, so a wrong import fails the test suite.

```
main.py                 composition root: the only place that knows every layer
config/settings.py      pydantic-settings; config/logging.json is the logging template
src/domain/             entities, value objects, errors (no framework or outer-layer imports)
src/application/        ports (protocols), DTOs, use cases
src/infrastructure/     in-memory repositories + mock data, logging, telemetry
src/interface/mcp/      FastMCP server, tools, tracing, runner
```

- Depend on abstractions (protocols in `application/ports`), not on concrete adapters.
- The server is stateless (`stateless_http=True`) so it scales horizontally. In-memory
  repositories are the only state and only suit mocks.
- Keep modules small (single responsibility).

### Adding a tool
1. Domain: entity, value object or error if needed.
2. Application: port method, DTO and a use case.
3. Infrastructure: implement the port (and mock data).
4. Interface: register the tool in `src/interface/mcp/tools/` with keyword-only `*, ctx: Context`,
   wrap the use case in `server_span(ctx, "<tool>")`, and wire it in `build_server`, `main.py`
   and the `use_cases` fixture in `tests/conftest.py` (`build_server` takes use cases positionally).
5. Tests mirroring the source path, and a request/response pair in `examples/`; also refresh
   `examples/responses/tools_list*.json` (`tests/test_examples.py` replays every request and
   compares it with its stored response, so update both when a tool changes).

## Python standards
- Use `async`/`await` for I/O-bound work and context managers for files, sessions and streams.
- Use `pathlib.Path` for paths and validate them (no directory traversal).
- Type-annotate public code. Line length 100 (ruff).
- Configuration comes from the environment through `pydantic-settings`. Never hardcode hosts,
  ports, URLs or model names. `MCP_HOST` and `MCP_PORT` are required; empty variables are ignored.
- Use only official, stable libraries. No pre-release, experimental or deprecated packages.
  Pin major versions and check the current stable version before choosing a dependency or
  Docker tag; do not rely on memory. Prefer the standard library when it is enough.
- The `mcp` SDK is pinned `>=1.9,<2`: the code subclasses `FastMCP` and reads
  `ctx.request_context.meta`, which a major release may change.

## Errors and security
- Validate inputs (ids, payloads, queries) before use, to reduce injection risk.
- No bare `except:` and no unlogged `except Exception:`. Catch specific exceptions and re-raise
  with context (`raise ... from err`). Domain errors are mapped to tool errors, not stack traces.
- Never commit secrets. `.env` is git-ignored; `.env.example` documents every variable.
- The server has no authentication (demo). Do not expose it publicly as is.
- Before making a repository public, check files and git history for secrets, personal data
  and machine-specific paths.

## Logging
- Standard `logging` with `logger = logging.getLogger(__name__)`; no `print` in application code.
- Levels: DEBUG internals, INFO lifecycle, WARNING non-fatal problems, ERROR failures.
- `config/logging.json` is a static template. The profile is chosen with `APP_ENV`
  (`local`: DEBUG, console + file; `development`: DEBUG, JSON; `production`: INFO, JSON).
  Explicit `LOG_*` variables override the profile. Setup code is in `src/infrastructure/logging/`.
- JSON output (always in the file, on stdout outside `local`) carries `trace_id` and `span_id`;
  sensitive `extra` keys are redacted. No log shipping is implemented: collect stdout.

## Tracing (OpenTelemetry, OTLP/HTTP)
- Enabled with `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` (base URL, for example
  `http://localhost:4318`; `/v1/traces` is added by the code).
- The caller's W3C `traceparent` travels in the MCP request `params._meta`, not in HTTP headers:
  the MCP client sends every request from a task created when the connection opens, so a header
  would attach all calls to the same parent.
- `tools/call <name>` and `tools/list` both create SERVER spans (`src/interface/mcp/tracing.py`, `traced_server.py`).
- The Python SDK client lists tools implicitly (without `_meta`) on the first `call_tool` of a
  session, creating an orphan trace. Clients should call `list_tools` explicitly after
  `initialize()`, with `_meta` (see `scripts/simulate_agent.py`).
- Spans are batched (about 5 s) and must be flushed on shutdown: `main.py` handles SIGTERM and
  Ctrl+C and calls `shutdown_tracing` and `shutdown_logging` in `finally`.

## Testing
- `pytest`, mirroring `src/` under `tests/`; must work from the repo root.
- Unit tests are fast and isolated: mock network, databases and disk.
- Arrange-Act-Assert. Cover the happy path and edge cases (empty input, missing files,
  corrupted data, missing env vars).
- Tracing tests use the `span_exporter` fixture in `tests/conftest.py` (one in-memory
  exporter installed per session, cleared before and after each test).

## Docker
- Multi-stage `Dockerfile`, non-root user, healthcheck on `/health`, no secrets in the image.
- `docker-compose.yml` is self-contained (server + Jaeger). `docker-compose.docker-env.yml`
  is for a shared `docker-env-net` network that already runs Jaeger. Do not run both: they
  compete for port 4318.
- The container must exit cleanly on SIGTERM, flushing logs and traces.