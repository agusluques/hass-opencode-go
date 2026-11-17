# Contributing

Thanks for helping maintain this fork of **OpenCode Go Conversation**.

## Development setup

```bash
./script/setup/bootstrap   # create .local/ha-venv and install dev dependencies
./script/develop           # run Home Assistant with the integration loaded
```

Home Assistant uses `config/configuration.yaml` and loads the integration from
`custom_components/` through `PYTHONPATH`. The dev container (`.devcontainer/`)
provides the same environment in VS Code or Codespaces.

## Before opening a PR

```bash
./script/check     # tests + lint + types + spelling + hassfest
```

If you changed behavior, also:

- add or update tests in `tests/`;
- update `README.md` when setup, models or troubleshooting change;
- add an entry under `Unreleased` in `CHANGELOG.md`.

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/), for example
`fix(api): refresh the catalog when a model is unknown`.

## Releasing

Releases are HACS-installable and must be tested as pre-releases first. See the
**Development → Releasing** section of the [README](README.md#releasing).

## Security

Never commit API keys, diagnostics with tokens, or real conversation logs. The
client talks to `https://opencode.ai/zen/go/v1`; review any change that touches
endpoints, authentication, model selection or streamed tool calls.
