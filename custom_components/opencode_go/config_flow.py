"""Config flow for OpenCode Go Conversation."""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)
import voluptuous as vol

from .const import (
    CONF_AI_TASK_MODEL,
    CONF_API_KEY,
    CONF_CONVERSATION_MODEL,
    CONF_IMAGE_GENERATION,
    CONF_MODEL,
    CONF_NAME,
    CONF_PROMPT,
    CONF_REASONING_EFFORT,
    CONF_REASONING_SUMMARY,
    CONF_RECOMMENDED,
    CONF_TEXT_VERBOSITY,
    DEFAULT_NAME,
    DOMAIN,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_REASONING_EFFORT,
    RECOMMENDED_REASONING_SUMMARY,
    RECOMMENDED_TEXT_VERBOSITY,
)
from .opencode_api import (
    OpenCodeGoApiError,
    OpenCodeGoAuth,
    OpenCodeGoClient,
    OpenCodeGoRateLimited,
    OpenCodeGoServerOverloaded,
)

_LOGGER = logging.getLogger(__name__)


async def _async_validate_api_key(hass, api_key: str) -> None:
    """Ensure the provided API key can list models."""
    session = async_get_clientsession(hass)
    client = OpenCodeGoClient(OpenCodeGoAuth(session, api_key))
    await client.list_models()


async def _async_fetch_models(hass, api_key: str) -> list[str]:
    """Fetch the live OpenCode Go catalog.

    There is no offline fallback: offering models from a stale snapshot is how
    users end up selecting a model their plan no longer includes.
    """
    session = async_get_clientsession(hass)
    client = OpenCodeGoClient(OpenCodeGoAuth(session, api_key))
    return await client.list_models(refresh=True)


class OpenCodeGoConversationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: ask for API key, then configure subentries."""

    VERSION = 3

    def __init__(self) -> None:
        super().__init__()
        self._api_key: str | None = None

    def _async_api_key_form(
        self, *, step_id: str, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Show the API key form for create, reconfigure, or reauth flows."""
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                await _async_validate_api_key(self.hass, api_key)
            except (
                OpenCodeGoApiError,
                OpenCodeGoRateLimited,
                OpenCodeGoServerOverloaded,
            ):
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Failed to validate OpenCode Go API key")
                errors["base"] = "cannot_connect"
            else:
                self._api_key = api_key
                return await self.async_step_models()

        return self._async_api_key_form(step_id="user", errors=errors)

    async def async_step_models(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the first model for the conversation agent and the AI Task."""
        if not self._api_key:
            return await self.async_step_user()

        if user_input is not None:
            conversation_model = str(user_input[CONF_CONVERSATION_MODEL])
            ai_task_model = str(user_input[CONF_AI_TASK_MODEL])
            return self.async_create_entry(
                title="OpenCode Go",
                data={CONF_API_KEY: self._api_key},
                subentries=[
                    {
                        "subentry_type": "conversation",
                        "data": {
                            **RECOMMENDED_CONVERSATION_OPTIONS,
                            CONF_MODEL: conversation_model,
                            CONF_NAME: DEFAULT_NAME,
                        },
                        "title": conversation_model.removeprefix("opencode-go/"),
                        "unique_id": None,
                    },
                    {
                        "subentry_type": "ai_task_data",
                        "data": {
                            **RECOMMENDED_AI_TASK_OPTIONS,
                            CONF_MODEL: ai_task_model,
                            CONF_NAME: DEFAULT_NAME,
                        },
                        "title": ai_task_model.removeprefix("opencode-go/"),
                        "unique_id": None,
                    },
                ],
            )

        errors: dict[str, str] = {}
        try:
            models = await _async_fetch_models(self.hass, self._api_key)
        except Exception:
            _LOGGER.exception("Failed to fetch the OpenCode Go model catalog")
            models = []
            errors["base"] = "cannot_connect"
        if not models and not errors:
            errors["base"] = "no_models"

        return self.async_show_form(
            step_id="models",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONVERSATION_MODEL): SelectSelector(
                        SelectSelectorConfig(options=list(models))
                    ),
                    vol.Required(CONF_AI_TASK_MODEL): SelectSelector(
                        SelectSelectorConfig(options=list(models))
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow updating the stored API key without reinstalling."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                await _async_validate_api_key(self.hass, api_key)
            except (
                OpenCodeGoApiError,
                OpenCodeGoRateLimited,
                OpenCodeGoServerOverloaded,
            ):
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Failed to validate OpenCode Go API key")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates={CONF_API_KEY: api_key},
                )

        return self._async_api_key_form(step_id="reconfigure", errors=errors)

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            "conversation": OpenCodeGoConversationSubentryFlow,
            "ai_task_data": OpenCodeGoAITaskSubentryFlow,
        }


class _BaseOpenCodeGoSubentryFlow(ConfigSubentryFlow):
    """Base flow for OpenCode Go subentries using model settings."""

    options: dict[str, Any]
    _init_data: dict[str, Any]

    @property
    def _is_new(self) -> bool:
        return self.source == "user"

    @property
    def _default_data(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def _supports_prompt_and_apis(self) -> bool:
        return False

    @property
    def _supports_image_generation_option(self) -> bool:
        return False

    SUBENTRY_TYPE = ""

    def _next_subentry_name(self) -> str:
        """Return the next default name for this subentry type.

        Names are counted per entity domain (conversation vs AI Task), so a
        conversation and an AI Task can both be called "OpenCode Go"; the
        second AI Task becomes "OpenCode Go 2".
        """
        entry = self._get_entry()
        used = {
            subentry.data.get(CONF_NAME)
            for subentry in entry.subentries.values()
            if subentry.subentry_type == self.SUBENTRY_TYPE
        }
        used.discard(None)
        if DEFAULT_NAME not in used:
            return DEFAULT_NAME
        index = 2
        while f"{DEFAULT_NAME} {index}" in used:
            index += 1
        return f"{DEFAULT_NAME} {index}"

    async def _async_model_options(self) -> list[str]:
        api_key = self._get_entry().data[CONF_API_KEY]
        return await _async_fetch_models(self.hass, api_key)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self.options = self._default_data.copy()
        self._init_data = {}
        return await self.async_step_init()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self.options = self._get_reconfigure_subentry().data.copy()
        self._init_data = {}
        return await self.async_step_init()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if self._get_entry().state != ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        options = self.options
        if user_input is not None:
            if user_input[CONF_RECOMMENDED]:
                data = self._default_data.copy()
                data[CONF_MODEL] = user_input[CONF_MODEL]
                data[CONF_NAME] = (
                    str(user_input.get(CONF_NAME) or "").strip()
                    or self._next_subentry_name()
                )
                if self._supports_image_generation_option:
                    data[CONF_IMAGE_GENERATION] = bool(
                        user_input.get(
                            CONF_IMAGE_GENERATION,
                            self._default_data.get(CONF_IMAGE_GENERATION, True),
                        )
                    )
                if self._supports_prompt_and_apis:
                    data[CONF_PROMPT] = (
                        user_input.get(CONF_PROMPT) or llm.DEFAULT_INSTRUCTIONS_PROMPT
                    )
                    # An untouched multi-select is absent from user_input; keep
                    # the recommended Assist API instead of silently disabling
                    # Home Assistant control.
                    selected_apis = user_input.get(CONF_LLM_HASS_API)
                    if selected_apis is None:
                        selected_apis = self._default_data.get(CONF_LLM_HASS_API, [])
                    data[CONF_LLM_HASS_API] = selected_apis
                return self._finalize_subentry(data)

            self._init_data = user_input
            return await self.async_step_advanced()

        try:
            model_options = await self._async_model_options()
        except Exception:
            _LOGGER.exception("Failed to fetch the OpenCode Go model catalog")
            return self.async_abort(reason="cannot_connect")

        if not model_options:
            return self.async_abort(reason="no_models")

        # Never preselect a model on a new configuration: the catalog changes
        # and a hardcoded default eventually stops being part of the plan.
        model_key: Any = vol.Required(CONF_MODEL)
        if options.get(CONF_MODEL) in model_options:
            model_key = vol.Required(
                CONF_MODEL,
                description={"suggested_value": options[CONF_MODEL]},
            )

        step_schema: dict = {
            model_key: SelectSelector(
                SelectSelectorConfig(options=list(model_options))
            ),
            vol.Optional(
                CONF_NAME,
                description={
                    "suggested_value": options.get(CONF_NAME)
                    or self._next_subentry_name()
                },
            ): str,
        }
        if self._supports_image_generation_option:
            step_schema[
                vol.Required(
                    CONF_IMAGE_GENERATION,
                    default=options.get(CONF_IMAGE_GENERATION, True),
                )
            ] = bool
        if self._supports_prompt_and_apis:
            hass_apis: list[SelectOptionDict] = [
                {"value": api.id, "label": api.name}
                for api in llm.async_get_apis(self.hass)
            ]
            step_schema.update(
                {
                    vol.Optional(
                        CONF_PROMPT,
                        description={
                            "suggested_value": options.get(
                                CONF_PROMPT, llm.DEFAULT_INSTRUCTIONS_PROMPT
                            )
                        },
                    ): TemplateSelector(),
                    vol.Optional(
                        CONF_LLM_HASS_API,
                        description={
                            "suggested_value": options.get(
                                CONF_LLM_HASS_API,
                                self._default_data.get(CONF_LLM_HASS_API),
                            )
                        },
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=cast(list[SelectOptionDict] | list[str], hass_apis),
                            multiple=True,
                        )
                    ),
                }
            )
        step_schema[
            vol.Required(
                CONF_RECOMMENDED,
                default=options.get(CONF_RECOMMENDED, True),
            )
        ] = bool

        return self.async_show_form(step_id="init", data_schema=vol.Schema(step_schema))

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        options = self.options

        if user_input is not None:
            data = {**self._init_data, **user_input}
            return self._finalize_subentry(data)

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REASONING_EFFORT,
                        default=options.get(
                            CONF_REASONING_EFFORT, RECOMMENDED_REASONING_EFFORT
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(options=["low", "medium", "high"])
                    ),
                    vol.Required(
                        CONF_REASONING_SUMMARY,
                        default=options.get(
                            CONF_REASONING_SUMMARY, RECOMMENDED_REASONING_SUMMARY
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=["auto", "short", "detailed", "off"]
                        )
                    ),
                    vol.Required(
                        CONF_TEXT_VERBOSITY,
                        default=options.get(
                            CONF_TEXT_VERBOSITY, RECOMMENDED_TEXT_VERBOSITY
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(options=["low", "medium", "high"])
                    ),
                }
            ),
        )

    def _finalize_subentry(self, data: dict[str, Any]) -> SubentryFlowResult:
        model = data.get(CONF_MODEL) or ""
        data[CONF_NAME] = (
            str(data.get(CONF_NAME) or "").strip() or self._next_subentry_name()
        )
        # The config entry title already says "OpenCode Go"; the subentry title
        # is only the model, so Home Assistant renders "<entry> <model>" without
        # repeating the integration name. The device and entity IDs use
        # CONF_NAME instead, so changing the model keeps them stable.
        title = model.removeprefix("opencode-go/") if model else DEFAULT_NAME

        if self._is_new:
            return self.async_create_entry(title=title, data=data)

        return self.async_update_and_abort(
            self._get_entry(),
            self._get_reconfigure_subentry(),
            data=data,
            title=title,
        )


class OpenCodeGoConversationSubentryFlow(_BaseOpenCodeGoSubentryFlow):
    """Flow for OpenCode Go conversation subentries."""

    SUBENTRY_TYPE = "conversation"

    @property
    def _default_data(self) -> dict[str, Any]:
        return RECOMMENDED_CONVERSATION_OPTIONS

    @property
    def _supports_prompt_and_apis(self) -> bool:
        return True


class OpenCodeGoAITaskSubentryFlow(_BaseOpenCodeGoSubentryFlow):
    """Flow for OpenCode Go AI task subentries."""

    SUBENTRY_TYPE = "ai_task_data"

    @property
    def _supports_image_generation_option(self) -> bool:
        return True

    @property
    def _default_data(self) -> dict[str, Any]:
        return RECOMMENDED_AI_TASK_OPTIONS
