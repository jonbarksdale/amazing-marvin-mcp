# Security Model

## Authentication

This MCP server authenticates to Amazing Marvin using a **full-access API token**
(`X-Full-Access-Token`). This token grants complete read/write access to the
Marvin account — there is no read-only mode (an Amazing Marvin API limitation).

The token is read from the `MARVIN_API_TOKEN` environment variable at startup.
It is never logged, never included in error messages, and excluded from
`__repr__`/`__str__` output on internal objects.

## Transport Security

- **STDIO transport only.** The server communicates over stdin/stdout with the
  parent process. No network listener is opened, so only the local process that
  spawns the server can interact with it.
- **HTTPS enforced.** All API calls use `https://serv.amazingmarvin.com/api`.
  The base URL is hardcoded and cannot be overridden. TLS certificate validation
  is enabled (httpx default).

## Authorization

MCP does not define an authorization layer. All 13 tools — including destructive
operations like `delete_item` and `mark_done` — are available to any connected
MCP client. The STDIO transport model mitigates this: only the process that
launched the server has access.

**If this server were ever exposed over HTTP/SSE transport, an authorization
layer would need to be added before deployment.**

## Token Handling Checklist

- Token sourced from environment variable, never from config files or CLI args
- Empty/missing token rejected at startup with a clear error
- Token stored in a private attribute (`_api_token`)
- `__repr__` and `__str__` do not expose the token (covered by tests)
- `.env` files excluded via `.gitignore`
- Error messages reference the token *name*, never its *value*
