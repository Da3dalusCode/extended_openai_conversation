# Changelog

## [1.3.2] - 2025-10-22
### Fixed
- **HA conversation import compatibility:** Remove hard dependency on `homeassistant.components.conversation.agent`; add a robust shim so `ConversationResult` works across HA versions that do/don’t expose that path.
- Silence future breakage by avoiding deprecated OptionsFlow assignment patterns (no explicit `self.config_entry = ...`).

### Changed
- More explicit routing: `auto` → reasoning models use **Responses API**; non-reasoning defaults to **Chat Completions**. User can still force either path.
- Debug logging: one line to show chosen path and capabilities.

## [1.3.1] - 2025-10-22
### Fixed
- Initial attempt to import `ConversationResult` from `conversation.agent` for newer HA builds.

## [1.3.0] - 2025-10-22
### Added
- **Reasoning-model support** via **Responses API** (adds `reasoning: {effort}` for reasoning models; omits sampling there).
- Clean **Assist** integration: returns a proper `ConversationResult` with `continue_conversation`.
- Config flow: API key on first screen; Options for model/strategy/limits.
