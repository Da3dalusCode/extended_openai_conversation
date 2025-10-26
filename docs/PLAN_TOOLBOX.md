# Toolbox Parity Plan Stub

## Planned Modules / Files
- `custom_components/extended_openai_conversation/conversation.py`: integrate orchestration, web search + MCP toggles.
- `custom_components/extended_openai_conversation/tools_orchestrator.py`: async loop handling for Responses vs Chat tool calls, depth caps.
- `custom_components/extended_openai_conversation/tools_builtin.py`: implement execute_service, add_automation, get_history, rest, scrape, composite, script, template.
- `custom_components/extended_openai_conversation/tools_web_search.py`: hosted web search adapter with reasoning vs chat paths.
- `custom_components/extended_openai_conversation/tools_mcp_bridge.py`: optional MCP client bridge with namespaced tools.
- `custom_components/extended_openai_conversation/config_flow.py`, `const.py`, `translations/en.json`: options UI for functions YAML + web search toggles with validation.
- `custom_components/extended_openai_conversation/openai_support.py`, `responses_adapter.py`, `model_capabilities.py`: routing hooks, schema helpers.
- `custom_components/extended_openai_conversation/manifest.json`: optional deps (e.g., `beautifulsoup4`) and metadata.
- `README.md`, `docs/PLAN_TOOLBOX.md`: documentation updates and manual test plan.

## Key Risks & Mitigations
- Async safety / event loop blocking → use HA executor helpers, streaming HTTPX timeouts, lazy imports for heavy deps.
- Tool abuse of non-exposed entities → reuse HA exposed-entity checks and guard by integration allow-lists.
- External calls (REST/scrape/web search/MCP) hanging → enforce per-tool timeout, payload caps, structured error responses.
- MCP / optional deps missing → feature-flag, detect import errors, return user-facing warnings without failing setup.
- Responses API schema regressions → centralize payload construction and continuation handling, cover with manual tests.

## Acceptance Tests Checklist
- [ ] Basic Assist Q&A without tools returns speech and continue flag as expected.
- [ ] `execute_service` on exposed entity executes; denied on non-exposed entity with clear message.
- [ ] `get_history` with small window returns summary/truncated data within caps.
- [ ] `rest` and `scrape` respect timeout/size limits and handle errors gracefully.
- [ ] `composite` chains at least two tools; exceeding depth limit yields safe stop message.
- [ ] Web search toggle off → no tool registration; on with reasoning model uses Responses tool continuation.
- [ ] Non-reasoning model attempts web search via Chat path; unsupported tool yields graceful degradation note.
- [ ] MCP bridge disabled → no effect; enabled with server available exposes namespaced tool and returns data.
- [ ] ConversationResult stays valid and continue_conversation logic unchanged for Assist.
