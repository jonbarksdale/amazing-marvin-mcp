# ROLE
You are a senior software engineer trained to plan and build MCP servers for LLM tool integration.

# TASK
Plan and implement a custom Amazing Marvin MCP server. Start by entering plan mode, designing the architecture, tool set, and response formatting strategy, then implement it.

# CONTEXT
We evaluated 6 existing Amazing Marvin MCP servers on GitHub and decided to build our own because:
- **logical-luke/amazing-marvin-mcp** (TypeScript, 47 tools) has the best capability coverage (full CRUD, calendar events, time blocks) but bloats context with too many tools and returns raw, untrimmed API responses.
- **lucadeleo/amazing-marvin-mcp** (Python, 9 tools) has the best context efficiency (25K char limit, markdown output, smart truncation) but lacks update, delete, and calendar event support.
- **bgheneti/Amazing-Marvin-MCP** (Python, 17 tools) sits in the middle but also lacks update/delete/calendar.
- The **marvin-cli** is stalled (last commit 2023) and missing mark-done, update, and delete commands.
- The API is simple enough (~33 endpoints) that building from scratch is faster than forking and trimming.

**Amazing Marvin API reference:** https://github.com/amazingmarvin/MarvinAPI (wiki + marvin-api.yaml)
- Auth: `X-API-Token` header (limited access) and `X-Full-Access-Token` header (full access, needed for `/doc/update`, `/doc/create`, `/doc/delete`, `/doc`)
- Base URL: `https://serv.amazingmarvin.com/api`
- Rate limits: 1 create/sec, 1 query/3sec, 1440 queries/day

**My use cases** — I track tasks in Marvin grouped in projects and folders. I need to:
1. Read today's tasks and overdue tasks
2. Browse project/folder structure
3. Create tasks (with scheduling, labels, parent project)
4. Update tasks (reschedule, edit title/notes)
5. Mark tasks done
6. Plan my day (view/manage time blocks)
7. Copy items from my work calendar into Marvin's calendar (create events with start time + duration)
8. Get labels for context

**Target tool set (~10 tools):**

| Tool | Endpoint |
|---|---|
| get_today | `GET /todayItems` |
| get_due | `GET /dueItems` |
| get_categories | `GET /categories` |
| get_children | `GET /children` |
| get_labels | `GET /labels` |
| create_task | `POST /addTask` |
| update_task | `POST /doc/update` (full access) |
| mark_done | `POST /markDone` |
| get_time_blocks | `GET /todayTimeBlocks` |
| create_event | `POST /addEvent` |

# ASSUMPTIONS
- Python with `mcp` SDK and `httpx` (async)
- STDIO transport (for Claude Code / Claude Desktop)
- API key from environment variable, never logged
- Response trimming from day one: truncate notes, cap response size, prefer markdown over raw JSON

# CONSTRAINTS
- Security is paramount: API key only in headers to amazingmarvin.com over HTTPS, never logged, never stored beyond what's needed
- Context efficiency: concise tool descriptions, trimmed/formatted responses (learn from lucadeleo's approach)
- ~10 focused tools, not 47. Only add tools that serve the use cases above.
- Built-in rate limiting matching Marvin's documented limits
- No mock mode — test against the real API

# VERIFICATION
- All tools work against the real Amazing Marvin API
- API key is never present in logs at any log level
- Response sizes stay reasonable (test with a populated account)
- Rate limiter correctly throttles when limits are approached
- Unit tests, integration tests, and E2E tests all pass with clean output
