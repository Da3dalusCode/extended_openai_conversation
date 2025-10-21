<!-- CHANGELOG.md -->
# Changelog

## 1.2.1 — 2025-10-21
### Fixed
- **Fresh install via HACS**: restored `ConfigFlow` symbol (HA expects `module.ConfigFlow`), and first-step API key prompt.  
- **Migration**: proper `async_migrate_entry()` using `hass.config_entries.async_update_entry` (no direct `entry.version` writes).  
- **Import-time crashes**: restored/guarded constants in `const.py` so optional modules can import safely.  
- **Options UI**: single-screen schema (no list-serialization errors), clean defaults.

### Changed
- Keep **non-streaming** Responses for reliability in Assist.
- Suppress `temperature/top_p` for GPT-5 (use `reasoning.effort`).

### Known limits
- Stateless per turn (dialog history off for now).
- Tools & memory scaffolded but disabled by default.

---

## 1.2.0 — 2025-10-21
### Added
- **GPT-5 support** via **Responses API**, with `reasoning.effort` (`low`, `medium`, `high`).  
- **Assist-compatible result** (`response.speech.plain.speech`, `continue_conversation`).  
- **Config-entry migration handler** to prevent “Migration handler not found”.  
- **Single-screen Options UI** (no blank arrow pages / list schema errors).

### Changed
- Default to **non-streaming** responses (streaming returns later when fully hardened).
- Suppress `temperature/top_p` for GPT-5.

### Fixed
- Removed legacy imports that referenced missing constants in some forks.  
- Avoided blocking calls on the event loop by using HA’s shared HTTPX client.
