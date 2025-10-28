## Toolbox & Options Parity Plan

### Scope Highlights
- Build a unified tools orchestrator ensuring identical behavior for chat vs reasoning paths, including depth/time limits and chat-log breadcrumbs.
- Implement built-in tools (`execute_service`, `add_automation`, `get_history`, `rest`, `scrape`, `composite`, `script`, `template`) with entity exposure enforcement, payload caps, and lazy imports (BeautifulSoup optional).
- Re-introduce Functions editor in Options flow with strong YAML validation, plus toggles for hosted web search and MCP bridging when available.
- Extend conversation pipeline to honor tool continuations for Responses API (`function_call`/`function_call_output`) and classic Chat Completions tool loops.
- Add hosted web search adapter with context sizing, location enrichment, and graceful no-op on unsupported chat models/backend.
- Optionally bridge MCP tools (namespaced) via lazy import, honoring timeouts and payload safeguards without impacting baseline when unavailable.

### Key Files / Modules
- `custom_components/extended_openai_conversation/`: `tools_orchestrator.py`, `tools_builtin.py`, `tools_web_search.py`, `tools_mcp_bridge.py`, `conversation.py`, `responses_adapter.py`, `config_flow.py`, `const.py`, `openai_support.py`, `services.py`, `services.yaml`.
- `manifest.json`, `translations/en.json`, `strings.json` (if legacy strings still referenced), `README.md`, `docs/` (this plan + potential future notes).

### Risks & Mitigations
- **Recursive tool loops**: enforce configurable depth/time limits and emit safe errors when exceeded.
- **Entity access control drift**: centralize exposure checks using HA permissions helpers; add clear user-facing error strings.
- **YAML validation regressions**: wrap parsing in try/except with schema verification and surface translations for misconfiguration.
- **Optional deps (bs4, MCP)**: lazy import and fall back with descriptive errors; include conditional manifest dependency for BeautifulSoup.
- **Hosted search availability mismatch**: introspect model/backend support; log info-level skip rather than raising.
- **Concurrency/event loop**: ensure all I/O uses async/httpx via HA shared client; offload blocking work with executor where required.

### Manual Validation Checklist
- Base conversation flow returns `ConversationResult` with language + response_type + `continue_conversation`.
- `execute_service` respects exposed entities and denies others with clear messaging.
- `get_history` returns bounded, summarized results.
- `rest` and `scrape` apply timeouts/size caps; `scrape` gracefully fails when `beautifulsoup4` missing.
- `composite` chains calls, enforces loop depth/time caps.
- Web search succeeds on reasoning model and no-ops with log on unsupported chat path; location payload included when enabled.
- MCP bridge disabled by default; when enabled with server it exposes namespaced tools and respects limits.
- Functions editor rejects malformed YAML without crashing Options flow.
- `query_image` service registered and uses consistent credential sourcing.
