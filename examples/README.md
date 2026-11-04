# Examples

JSON-RPC requests for the MCP server and the responses it returns.

```
requests/     bodies to send to POST /mcp
responses/    what the server answers (same file names)
requests.http same requests for the VS Code "REST Client" extension
```

## Run one

```bash
curl -s -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d @examples/requests/get_ticket_info.json
```

Use the port you set in `MCP_PORT`. Headers use double quotes and the body comes
from a file, so the command works the same in bash, cmd and PowerShell
(`curl.exe` in PowerShell).

## Things worth knowing

- **The HTTP body is Server-Sent Events**, not plain JSON:
  `event: message` followed by `data: {...}`. The files in `responses/` hold
  only the JSON-RPC payload from the `data:` line.
- **A failing tool is still HTTP 200.** The error is in the result:
  `"isError": true` with the message in `content[0].text`. See the `error_*` files.
- **Tracing:** `get_ticket_info_with_traceparent.json` shows how a caller passes
  its trace context inside `params._meta.traceparent`. The server log then shows
  that `trace_id`.
- **Mock data:** `create_ticket` returns `T-1004` on a freshly started server,
  because tickets live in memory and `T-1001` to `T-1003` are seeded.
- Responses were captured from a running server. `tests/test_examples.py` replays
  every request and fails if a response drifts, ignoring timestamps and the
  pydantic version in error URLs.
