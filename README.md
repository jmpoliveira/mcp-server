# mcp-server

[![CI](https://github.com/jmpoliveira/mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/jmpoliveira/mcp-server/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)

A generic [Model Context Protocol](https://modelcontextprotocol.io) server over **streamable HTTP**, built with Python and the official MCP SDK. It ships with three mock tools (customers and support tickets) and a layered structure so the mocks can be replaced by real systems without touching the tools.

## Quick start

```bash
cp .env.example .env     # set MCP_HOST and MCP_PORT
make install
make run                 # http://127.0.0.1:3000/mcp
```

Run `make help` for every command (`test`, `lint`, `typecheck`, `check`, `docker-up`).

## Tools

| Tool | Type | Description |
|------|------|-------------|
| `search_customers` | read-only | Search customers by id, name, email or company |
| `get_ticket_info` | read-only | Get a ticket by id (e.g. `T-1001`) |
| `create_ticket` | write | Create a ticket for an existing customer |

Mock data lives in `src/infrastructure/persistence/mock_data.py` (customers `C-001`..`C-004`, tickets `T-1001`..`T-1003`). Tickets created at runtime are kept in memory and lost on restart.

## Architecture

Clean Architecture with four layers. Dependencies only point inwards.

```
main.py                              composition root: the only place that knows every layer
config/settings.py                   environment configuration (pydantic-settings)
src/
  domain/                            enterprise rules, pure Python
    entities/                          Customer, Ticket
    value_objects/                     TicketId, TicketPriority, TicketStatus
    errors.py
  application/                       use cases and the ports they need
    ports/                             CustomerRepository, TicketRepository (protocols)
    dto/                               output models returned by use cases
    use_cases/                         SearchCustomers, GetTicketInfo, CreateTicket
  infrastructure/                    adapters implementing the ports
    persistence/                       in-memory repositories and mock data
    logging/                           structured logging (queue, JSON formatter, filters)
    telemetry.py                       OpenTelemetry tracer setup (OTLP/HTTP)
  interface/                         delivery mechanism
    mcp/                               FastMCP server and tool definitions
tests/                               mirrors src/, plus architecture/ rule checks
```

```
interface ----> application ----> domain
infrastructure -> application ----> domain
```

- `domain` imports nothing from the project or from any framework.
- `application` knows only `domain` and its own ports. Use cases return DTOs, so the MCP layer never touches entities.
- `infrastructure` and `interface` depend on `application` but never on each other.
- `tests/architecture/test_dependency_rule.py` fails the build if an import breaks these rules.

To use a real backend, write adapters that satisfy the two ports in `src/application/ports/` and swap them in `main.py`. Use cases and tools stay unchanged.

The server is stateless (`stateless_http=True`), so it can run as several replicas behind a load balancer. The in-memory repositories are the only state, which is why they only suit mocks.

## Configuration

Copy `.env.example` to `.env`. `MCP_HOST` and `MCP_PORT` are required; the server refuses to start without them.

## Run locally

```bash
pip install -e ".[dev]"
MCP_HOST=127.0.0.1 MCP_PORT=3000 python main.py
```

- MCP endpoint: `http://127.0.0.1:3000/mcp`
- Health check: `http://127.0.0.1:3000/health`

## Run with Docker

```bash
docker compose up --build
```

The endpoint is published at `http://localhost:3000/mcp`.

## Test

```bash
make test      # pytest
make check     # ruff + pyright + pytest, the same as CI
```

## Logging

Logging is configured in one place: `config/settings.py` (environment variables) plus `config/logging.json` (static structure). The code lives in `src/infrastructure/logging/`.

### Behaviour by environment

`APP_ENV` selects a profile. Any explicit `LOG_*` variable overrides the profile.

| | `local` | `development` | `production` (default) |
|---|---|---|---|
| Level | `DEBUG` | `DEBUG` | `INFO` |
| Terminal format | readable line | JSON | JSON |
| JSONL file | `logs/mcp-server.log.jsonl` | off | off |

Precedence: explicit `LOG_*` variable > `APP_ENV` profile > built-in default. `production` is the default on purpose, so a forgotten `APP_ENV` never turns debug logging or log files on.

| Variable | Meaning |
|---|---|
| `APP_ENV` | `local`, `development` or `production` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | `console` or `json` (terminal output only; the file is always JSON) |
| `LOG_FILE_ENABLED` | `true`/`false`, overrides the profile |
| `LOG_FILE` | path of the JSONL file (rotates at 10 MB, 10 backups) |
| `LOG_ACCESS` | `true` to log one line per HTTP request (uvicorn access log) |
| `LOG_MAX_MESSAGE_CHARS` | cap for the message and exception message (200-12000, default 4000) |
| `LOG_MAX_STACKTRACE_CHARS` | cap for the stacktrace (200-12000, default 6000) |
| `LOG_QUEUE_SIZE` | size of the in-memory log queue (minimum 100, default 10000) |
| `SERVICE_VERSION` | value of the `version` field |
| `MCP_SERVER_NAME` | name the MCP server reports to clients (default `mcp-server`) |
| `OTEL_SERVICE_NAME` | value of the `service` field and the tracing service name (default `mcp-server`) |

### JSON schema

One object per line, UTC timestamps:

```json
{"timestamp": "2026-11-04T10:00:00.123+00:00", "level": "INFO", "message": "Tool get_ticket_info called",
 "logger": "src.interface.mcp.tools.ticket_tools", "service": "mcp-server", "env": "production", "version": "0.1.0",
 "trace_id": "0af7651916cd43dd8448eb211c80319c", "span_id": "b7ad6b7169203331",
 "module": "ticket_tools", "function": "get_ticket_info_tool", "line": 34}
```

Fields passed with `extra={...}` are added at the end. Errors add `exc_type`, `exc_message` and `stacktrace`. `trace_id` and `span_id` are `null` outside a span. Message and stacktrace are capped; with the default caps a line stays below the 16 KiB at which Docker splits log lines (fields added with `extra` are not capped).

### Design notes

- Records go through a bounded queue to a listener thread, so logging never blocks a request. If the queue fills up, records are dropped and counted.
- Values passed through `extra` whose name looks sensitive (`password`, `token`, `authorization`, `*_secret`, ...) are replaced by `***`. Secrets written into the message text cannot be detected: never log them.
- Everything, uvicorn included, goes through the same pipeline, so stdout contains only JSON in `development` and `production`.
- In containers, collect stdout. The file is meant for local runs.

## Examples

`examples/` has ready-to-run JSON-RPC requests, the matching responses, and an `.http` file for the VS Code REST Client. See `examples/README.md`.

## Observability (OpenTelemetry)

Tracing is off by default. To enable it, set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` (base URL, for example `http://localhost:4318`). Spans are exported over OTLP/HTTP, and every log line carries `trace_id` and `span_id`.

The caller sends its W3C trace context inside the MCP request `_meta` (`traceparent`, optionally `tracestate` and `baggage`). Each tool call becomes a `tools/call <name>` SERVER span, and each tool listing a `tools/list` SERVER span, both continuing that trace, so discovery and execution appear in the same flow. Header propagation is deliberately not used: the MCP client sends all requests from a task created when the connection opens, so a header would attach every call to the same parent.

**Client note:** the Python MCP SDK's `call_tool` lists tools by itself (without `_meta`) the first time a tool is called in a session, which creates a separate, orphan `tools/list` trace. Avoid it by listing tools explicitly right after `initialize()`, inside a span, passing the context: `session.list_tools(params=PaginatedRequestParams(_meta=PaginatedRequestParams.Meta.model_validate(meta)))`. See `scripts/simulate_agent.py`.

`docker compose up --build` also starts Jaeger. If you already run Jaeger in a shared setup (for example a `docker-env` project on the network `docker-env-net`), use `docker compose -f docker-compose.docker-env.yml up --build` instead (it reads `.env`, and docker-env must be running first so the external network exists), and do not run both: they would compete for port 4318. Open http://localhost:16686 and look for the `mcp-server` service.

### Troubleshooting: no traces in Jaeger, `trace_id` is `null`

Look at the startup log first:

| Startup line | Meaning |
|---|---|
| `Tracing is disabled` | `OTEL_ENABLED` is not `true`. Nothing is exported. `trace_id`/`span_id` are `null`, unless the request carries a `traceparent` in `_meta`: then logs show the caller's ids. |
| `Tracing enabled (... exporter=http://.../v1/traces)` | Tracing works. Logs inside a tool call carry ids. Startup and access logs are outside any span, so `null` there is normal. |
| `WARNING ... Transient error ... retrying` | The exporter cannot reach the endpoint: wrong host/port, or Jaeger is not listening there. |

Endpoint by setup: `http://localhost:4318` when the server runs on your machine and Jaeger in compose; `http://jaeger:4318` when both run in compose. In Jaeger's UI pick the service `mcp-server` (the value of `OTEL_SERVICE_NAME`) and widen the time range. Spans are sent in batches every 5 seconds.

### Testing without the agent

1. With a `curl` request carrying a `traceparent` in `_meta`:

```bash
curl -s -X POST http://localhost:3000/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_ticket_info","arguments":{"ticket_id":"T-1001"},"_meta":{"traceparent":"00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}}}'
```

The server log shows `"trace_id": "0af7651916cd43dd8448eb211c80319c"` in JSON format, or `[0af76519]` in the console format (`APP_ENV=local`). In Jaeger, search for that trace id; its span shows a missing parent because the caller span was never exported.

2. With the agent simulator, which produces a complete `agent -> mcp-server` trace:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  python scripts/simulate_agent.py --url http://localhost:3000/mcp
```

## Security notes

**Limitations of this demo:** no authentication or authorization, in-memory state only, mock data. Do not expose it publicly as is: put it behind an MCP gateway or reverse proxy that handles authentication and authorization. Tool inputs are validated in the domain (value objects and entities) and in the use cases, and `create_ticket` is annotated as a write tool so clients can ask for confirmation.

## License

[MIT](LICENSE)