<!-- README.md -->
# Extended OpenAI Conversation (Home Assistant)

**A drop-in conversation agent for Home Assistant with first-class GPT-5 support.**  
Works with Assist pipelines, uses OpenAI’s **Responses API** for reasoning models, and keeps memory/tools **optional** and **off by default** for reliability.

> This fork focuses on **stable voice UX** and **GPT-5 compatibility**. The local memory/RAG layer is scaffolded but **disabled by default** until the core path is rock-solid.

---

## Why use this?

- **GPT-5** via **Responses API**, including `reasoning.effort: low|medium|high`
- Clean, deterministic system prompt; safe default tone
- Plays nice with **Assist**: correct result shape and `continue_conversation`
- **Non-streaming by design** (keeps TTS stable while streaming is hardened)
- Memory/RAG **scaffolded** but **off** (easy to enable later)

---

## Requirements

- Home Assistant 2024.6+ (newer versions fine)
- A working OpenAI API key (or a compatible endpoint)
- Internet connectivity from HA to your endpoint

---

## Installation

### Option A — HACS (recommended)

1. In HACS, add this repository as a **Custom repository** (Category: *Integration*).  
2. Install **Extended OpenAI Conversation**.  
3. **Restart Home Assistant**.  
4. Go to **Settings → Devices & Services → Add Integration** and choose **Extended OpenAI Conversation**.  
5. Enter your **OpenAI API key**.  
   - Leave **Base URL** as `https://api.openai.com/v1` unless using a compatible proxy.  
6. Finish the wizard.

### Option B — Manual

Copy `custom_components/extended_openai_conversation` to `/config/custom_components` on your HA host → **Restart** → add the integration as above.

---

## Assign to your Voice Assistant

1. **Settings → Voice assistants** → select your assistant.  
2. Under **Conversation agent**, pick **Extended OpenAI Conversation**.  
3. You can leave **Prefer handling commands locally** enabled—Assist will still short-circuit simple HA intents locally.

---

## Configuration & Options

These settings are available from the integration’s **Configure** dialog.

| Option | What it does | Recommended |
|---|---|---|
| **API key, Base URL** | OpenAI credentials and endpoint | Required; default URL for OpenAI |
| **Model** | Name of the model | `gpt-5` |
| **Model strategy** | Auto/force Chat/force Responses | **Auto** |
| **Use Responses API** | Use Responses when supported | **On** |
| **Reasoning effort** | GPT-5 planning depth | `low` or `medium` |
| **Max completion tokens** | Output length on Responses API | `1024–2048` for long answers |
| **Temperature / Top-P** | Sampling controls | **Ignored by GPT-5** (applied to non-reasoning models) |
| **Context threshold / Truncation** | Token budget if dialog history is enabled | For large windows: threshold `32000`, strategy `keep_latest` (future) |

**Notes**

- GPT-5 **ignores** `temperature/top_p`; set **Reasoning effort** instead.  
- **Streaming** is intentionally **disabled** in this release to keep TTS/Assist deterministic.  
- **Dialog history** and **tools/memory** are **off** for now; router patterns won’t trigger external tools yet.

---

## Upgrade (HACS)

1. HACS → **Integrations** → open this repo.  
2. If **Update** is visible, click it. Otherwise **⋮ → Reload data**, then **Reinstall** → select the newest version.  
3. **Restart Home Assistant**.  
4. Reopen the integration’s **Configure** to verify options.

If HACS doesn’t show the update:
- Ensure your Git tag is **`vX.Y.Z`** and `manifest.json` has `"version": "X.Y.Z"` (tag **with** `v`, manifest **without**).  
- In HACS, **⋮ → Update information** to refresh the cache.

---

## Troubleshooting

- **“Migration handler not found …” banner**  
  Update to ≥1.2.1. This fork ships a proper `async_migrate_entry()` and uses HA’s `async_update_entry` to normalize versions.

- **Options screen fails / blank arrows**  
  The options schema now returns a dict (no raw lists), which the UI can serialize. If you still see issues, clear browser cache and reload.

- **OpenAI 400: “Unsupported parameter: temperature”**  
  Happens if `temperature` is sent to GPT-5 reasoning. We suppress classic sampling params for GPT-5 and use `reasoning.effort`.

---

## Privacy

Prompts are sent to OpenAI (or your configured compatible endpoint). No local memories are written unless you explicitly enable the memory layer later.

---

## Roadmap

- In-session dialog history (token-budgeted)
- Opt-in memory write/search tools
- Streaming once the Assist TTS path is robust with partials

---

## Credits

Based on the original project by **@jekalmin**. This fork focuses on GPT-5 compatibility and voice reliability.
