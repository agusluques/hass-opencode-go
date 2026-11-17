# OpenCode Go

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.3%2B-18BCF2?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/agusluques/hass-opencode-go-conversation?color=3DDC97)](../../releases)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)

A Home Assistant custom integration that turns **[OpenCode Go](https://opencode.ai/console/go)** models into Assist conversation agents, AI Tasks and an image generator. Ask your home questions, control entities with the Assist API, generate structured data or images — all billed through your OpenCode Go subscription.

> This is the community fork maintained at
> [`agusluques/hass-opencode-go-conversation`](https://github.com/agusluques/hass-opencode-go-conversation),
> based on the original work by [@avegao](https://github.com/avegao).

## Features

- **Conversation agents** — one agent per model, with streaming responses and multi-turn history.
- **Assist control** — expose the Home Assistant LLM API so the model can call tools and control entities.
- **AI Task support** — generate structured data with `ai_task.generate_data`.
- **Image generation** — `ai_task.generate_image` through the Responses models
  (`gpt-5.6-luna`, `gpt-6-luna`, `grok-4.7`).
- **All Go protocols** — OpenAI Chat Completions, Responses, Anthropic Messages
  and Google Gemini, all routed from the live catalog.
- **No stale defaults** — you pick the model while configuring the agent; if OpenCode retires it, you get an actionable error instead of a broken agent.
- **Attachments** — images and PDFs where the selected model supports them.
- **HACS ready** — standard custom-integration layout for HACS 2.x.

## Requirements

| Requirement | Details |
| --- | --- |
| Home Assistant | 2026.3.0 or newer |
| OpenCode Go | Active subscription and API key |
| HACS | Optional, only for HACS installation |

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=agusluques&repository=hass-opencode-go-conversation&category=integration)

1. Open HACS → **Integrations** → **⋮** → **Custom repositories**.
2. Add `https://github.com/agusluques/hass-opencode-go-conversation` as an **Integration**.
3. Search for **OpenCode Go**, install it and restart Home Assistant.

### Manual

1. Download the latest release and copy `custom_components/opencode_go_conversation`
   into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **OpenCode Go** and paste your API key
   (create one at <https://opencode.ai/auth>).
3. The integration opens the **Add conversation agent** flow:
   - **Model** — required; the list is loaded live from your catalog.
   - **Recommended model settings** — keep this on to use the suggested prompt,
     Assist API exposure and reasoning settings, or turn it off to tune them.
4. (Optional) Add more agents, one per model, or an **AI Task** entity for
   structured data and image generation.
5. In **Settings → Voice assistants**, assign the agent to your Assist pipeline.

Use **Reconfigure** on the integration entry to rotate the API key, or on a
subentry to change the model and reasoning settings.

## Models and routing

OpenCode Go splits its catalog across four protocols. The integration reads
`https://opencode.ai/zen/go/v1/models`, and derives each model's endpoint from
the catalog's own `api` metadata:

| Catalog `api` key | Endpoint used |
| --- | --- |
| `chat-completions` | `/chat/completions` |
| `responses` | `/responses` |
| `messages` | `/messages` |
| `generate-content` | `/models/{model}:streamGenerateContent` (Gemini) |

Each protocol also uses the `base_url` published in the catalog, so requests go
to the same endpoint the official OpenCode clients use. The catalog is cached
for an hour, refreshed when a model picker is opened and re-fetched whenever a
request refers to an unknown model or the API says the model is no longer in
the plan. There is **no hardcoded model list and no default model**.

## Image generation

Image generation is exposed through the AI Task platform:

1. Add an **AI Task** subentry with a Responses model
   (`gpt-5.6-luna`, `gpt-6-luna` or `grok-4.7`).
2. Set it as the preferred image entity in **Settings → Devices & Services →
   AI Task**, or call the service directly:

   ```yaml
   action: ai_task.generate_image
   data:
     task_name: logo
     instructions: A flat teal terminal icon on a dark background
     entity_id: ai_task.gpt_6_luna
   ```

The generated PNG is stored in the AI Task media folder, so it can be used in
dashboards, notifications and automations. Only Responses models advertise this
feature; chat, Anthropic and Google models in the Go plan are text-only.

## Troubleshooting

| Symptom | Meaning and fix |
| --- | --- |
| `Model … isn't included in OpenCode Go` | The model was removed from the plan. Reconfigure the agent and pick a current model; the catalog is refreshed automatically. |
| `cannot_connect` while adding an agent | The catalog could not be fetched. Check connectivity to `opencode.ai` and try again. |
| `no_models` while adding an agent | The catalog returned no model this client can talk to. Update the integration. |
| `API error 401` | The API key is invalid or was revoked. Use **Reconfigure** to paste a new one. |
| `API error 429` | OpenCode Go rate limit or monthly allowance reached. Wait or check your plan usage. |
| `MissingSessionID` | Should not happen with this integration; please open an issue with logs. |
| `This OpenCode Go model trains on request data` | Enable paid training endpoints in your OpenCode console privacy settings, or pick another model. |
| `The selected model cannot generate images` | Image generation requires a Responses model (`gpt-5.6-luna`, `gpt-6-luna`, `grok-4.7`). |

Enable debug logging from the integration page before capturing logs:

```yaml
logger:
  logs:
    custom_components.opencode_go_conversation: debug
```

## Development

### Local environment

```bash
./script/setup/bootstrap   # create .local/ha-venv and install dev deps
./script/develop           # start Home Assistant with config/ at :8123
```

The integration is loaded from `custom_components/` through `PYTHONPATH`, and
`config/configuration.yaml` is a minimal dev configuration. Useful commands:

| Command | What it does |
| --- | --- |
| `./script/test` | Run the pytest suite (`--cov` for coverage) |
| `./script/lint` | Format and autofix with Ruff |
| `./script/lint-check` | Verify formatting and lint without writing |
| `./script/type-check` | Run `ty` |
| `./script/hassfest` | Validate the integration against Home Assistant rules |
| `./script/spell-check` | Run codespell |
| `./script/check` | Everything above, in one go |

### Dev container

`.devcontainer/` defines a reproducible VS Code development container (Python
3.14, Home Assistant, HACS preinstalled, port 8123 forwarded). Open the
repository in VS Code and run **Dev Containers: Reopen in Container**, or open
it in a GitHub Codespace. On first creation it bootstraps the Python
environment; then run `./script/develop` and open <http://localhost:8123>.
This is the quickest way to test a change end-to-end without touching your real
Home Assistant installation.

### Releasing

HACS installs **releases**, so a release must be tested before it is published
as latest:

1. **Bump the version** in `custom_components/opencode_go_conversation/manifest.json`
   and `pyproject.toml`, and move the changes in `CHANGELOG.md` from
   `Unreleased` to the new version.
2. **Validate locally**: `./script/check` and `./script/hassfest`.
3. **Tag a pre-release**:

   ```bash
   git tag v0.4.0-beta.1
   git push origin v0.4.0-beta.1
   gh release create v0.4.0-beta.1 --prerelease --generate-notes
   ```

4. **Test it through HACS**: in a scratch Home Assistant (the dev container is
   ideal), add this repository as a custom repository, open the integration,
   use **Download** → version selector → pick the pre-release, restart, and
   exercise setup plus a conversation.
5. **Promote it**: create the final release with `gh release create v0.4.0`.
   HACS only offers releases whose tag matches the manifest version, so keep
   both in sync.

## Contributing

Issues and pull requests are welcome. Run `./script/check` before opening a PR
and describe how you tested the change. Please do not include API keys or real
conversation logs.

## License

[GPL-3.0](LICENSE)
