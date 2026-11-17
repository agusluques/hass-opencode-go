# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2026-11-17

### Changed

- Repository, Python project and integration metadata renamed from
  `hass-opencode-go-conversation` to `hass-opencode-go`; the Home Assistant
  domain stays `opencode_go_conversation` so existing installs keep working.
- Client user agent updated to `hass-opencode-go/0.4.1`.

## [0.4.0] - 2026-11-17

### Added

- Gemini support: models exposing the `generate-content` protocol are routed to
  `/models/{model}:streamGenerateContent` on the catalog's Google base URL.
- Image generation through `ai_task.generate_image` for Responses models
  (`gpt-5.6-luna`, `gpt-6-luna`, `grok-4.7`), stored in the AI Task media folder.
- Every protocol now uses the `base_url` published in the model catalog, so
  OpenAI, Anthropic and Google requests hit the same endpoints as the official
  OpenCode clients.
- `supports_image_generation()` helper and tests for Google payloads, Google
  SSE events and image generation.

### Changed

- The integration is now named **OpenCode Go** instead of "OpenCode Go
  Conversation".
- Agents and devices are named after the model only, so the Assist picker shows
  "OpenCode Go deepseek-v4.1-flash" without repeating the integration name.
  Existing subentries are migrated automatically.
- "Control Home Assistant" is preselected in the form and preserved when
  "Recommended model settings" is left checked.

### Fixed

- The **Assist** checkbox appeared not to work: an untouched multi-select was
  saved as an empty list, silently disabling Home Assistant control even when
  the recommended settings were selected.

## [0.3.0] - 2026-11-17

### Added

- Model catalog is read from `GET /models` at runtime, including each model's
  wire protocol from its `api` metadata.
- Catalog refresh when the model picker opens, during setup and whenever a
  request refers to an unknown model.
- Dedicated error for models removed from the OpenCode Go plan, with a hint to
  pick a current model.

### Changed

- The model is now required during setup and is no longer preselected: there is
  no default model to go stale.
- The config flow aborts with `cannot_connect` / `no_models` instead of falling
  back to a stale model snapshot.
- Brand assets (icons and wordmark) were redrawn and regenerated for HACS and
  Home Assistant brand folders.
- README rewritten with setup, troubleshooting, development and release
  instructions. The Spanish README was removed.

### Fixed

- Conversations failed with `Generation.ModelNotInGo` because the hardcoded
  default `deepseek-v4-flash` was no longer part of the plan.
- Models added to OpenCode Go after a release (for example
  `deepseek-v4.1-flash`, `gpt-6-luna`, `grok-4.7`, `qwen4-max`) were missing
  from the picker, while 13 retired models were still listed.

### Removed

- Hardcoded model-to-endpoint table and the docs-snapshot fallback.
- Inherited GitHub Actions workflows and Dependabot configuration. This fork is
  validated locally with `./script/check`.

## [0.2.0] - 2026-09-04

### Added

- Model-aware routing and protocol-specific request/SSE adapters for the
  Responses, OpenAI-compatible and Anthropic OpenCode Go endpoints.
- Per-conversation `x-opencode-session` header and integration user agent.
- Support for Home Assistant tool schema serialization.

### Fixed

- Request bodies and streaming responses aligned with the OpenCode Go contract.

## [0.1.0] - 2026-07-26

### Added

- Initial OpenCode Go Conversation integration.
- API key config flow, conversation agent and AI Task support.
- HACS-compatible repository layout and initial brand assets.

[Unreleased]: https://github.com/agusluques/hass-opencode-go/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/agusluques/hass-opencode-go/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/agusluques/hass-opencode-go/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/agusluques/hass-opencode-go/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/agusluques/hass-opencode-go/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/agusluques/hass-opencode-go/releases/tag/v0.1.0
