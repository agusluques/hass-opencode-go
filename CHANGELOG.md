# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/agusluques/hass-opencode-go-conversation/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/agusluques/hass-opencode-go-conversation/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/agusluques/hass-opencode-go-conversation/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/agusluques/hass-opencode-go-conversation/releases/tag/v0.1.0
