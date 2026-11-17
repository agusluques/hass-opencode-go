"""AI Task platform for the OpenCode Go integration."""

from __future__ import annotations

import base64
from json import JSONDecodeError
import logging
from typing import Any

from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.json import json_loads

from .const import (
    CONF_IMAGE_GENERATION,
    CONF_MODEL,
    CONF_NAME,
    CONF_REASONING_EFFORT,
    CONF_REASONING_SUMMARY,
    CONF_TEXT_VERBOSITY,
    DOMAIN,
    RECOMMENDED_REASONING_EFFORT,
    RECOMMENDED_REASONING_SUMMARY,
    RECOMMENDED_TEXT_VERBOSITY,
)
from .conversation import MAX_TOOL_ITERATIONS, async_run_chat_log
from .opencode_api import (
    OpenCodeGoAuth,
    OpenCodeGoClient,
    supports_image_generation,
)

_LOGGER = logging.getLogger(__name__)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_size(data: bytes) -> tuple[int | None, int | None]:
    """Return the width and height of a PNG payload."""
    if len(data) < 24 or not data.startswith(_PNG_SIGNATURE):
        return None, None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    api_key = hass.data[DOMAIN][entry.entry_id]["api_key"]
    for subentry in entry.subentries.values():
        if subentry.subentry_type != "ai_task_data":
            continue
        async_add_entities(
            [OpenCodeGoAITaskEntity(hass, entry, api_key, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class OpenCodeGoAITaskEntity(ai_task.AITaskEntity):
    """AI Task entity backed by OpenCode Go."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api_key: str,
        subentry: ConfigSubentry,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._subentry = subentry
        self._api_key = api_key
        self._attr_unique_id = subentry.subentry_id
        features = (
            ai_task.AITaskEntityFeature.GENERATE_DATA
            | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS
        )
        model = subentry.data.get(CONF_MODEL)
        if (
            isinstance(model, str)
            and supports_image_generation(model)
            and subentry.data.get(CONF_IMAGE_GENERATION, True)
        ):
            features |= ai_task.AITaskEntityFeature.GENERATE_IMAGE
        self._attr_supported_features = features

    @property
    def _options(self) -> Any:
        return self._subentry.data

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the configured model without tying entity IDs to it."""
        return {"model": self._options.get(CONF_MODEL)}

    @property
    def _model(self) -> str:
        """Return the configured model or explain how to pick one."""
        model = self._options.get(CONF_MODEL)
        if not isinstance(model, str) or not model.strip():
            raise HomeAssistantError(
                "No OpenCode Go model is configured. Open the integration "
                "options and choose a model from the catalog."
            )
        return model

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._subentry.subentry_id)},
            "name": self._options.get(CONF_NAME) or self._subentry.title,
            "manufacturer": "OpenCode",
            "entry_type": dr.DeviceEntryType.SERVICE,
        }

    async def _async_generate_image(
        self,
        task: ai_task.GenImageTask,
        chat_log: conversation.ChatLog,
    ) -> ai_task.GenImageTaskResult:
        """Generate an image through the Responses ``image_generation`` tool."""
        model = self._model
        conversation_id = chat_log.conversation_id or f"{self.entity_id}-image"
        client = OpenCodeGoClient(
            OpenCodeGoAuth(async_get_clientsession(self.hass), self._api_key)
        )
        encoded = await client.async_generate_image(
            model=model,
            instructions=task.instructions,
            session_id=conversation_id,
        )
        image_data = base64.b64decode(encoded)

        width, height = _png_size(image_data)
        return ai_task.GenImageTaskResult(
            image_data=image_data,
            conversation_id=conversation_id,
            mime_type="image/png",
            width=width,
            height=height,
            model=model,
        )

    async def _async_generate_data(
        self,
        task: ai_task.GenDataTask,
        chat_log: conversation.ChatLog,
    ) -> ai_task.GenDataTaskResult:
        client = OpenCodeGoClient(
            OpenCodeGoAuth(async_get_clientsession(self.hass), self._api_key)
        )

        await async_run_chat_log(
            chat_log=chat_log,
            client=client,
            model=self._model,
            entity_id=self.entity_id,
            reasoning_effort=self._options.get(
                CONF_REASONING_EFFORT, RECOMMENDED_REASONING_EFFORT
            ),
            reasoning_summary=self._options.get(
                CONF_REASONING_SUMMARY, RECOMMENDED_REASONING_SUMMARY
            ),
            text_verbosity=self._options.get(
                CONF_TEXT_VERBOSITY, RECOMMENDED_TEXT_VERBOSITY
            ),
            instructions_suffix=_format_structure_instruction(task),
            max_iterations=MAX_TOOL_ITERATIONS,
        )

        if not isinstance(chat_log.content[-1], conversation.AssistantContent):
            raise HomeAssistantError(
                "Last content in chat log is not an AssistantContent"
            )

        text = chat_log.content[-1].content or ""
        if not task.structure:
            return ai_task.GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=text,
            )

        try:
            data = json_loads(text)
        except JSONDecodeError as err:
            _LOGGER.error("Failed to parse JSON response: %s. Response: %s", err, text)
            raise HomeAssistantError(
                "Error with OpenCode Go structured response"
            ) from err

        return ai_task.GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=data,
        )


def _format_structure_instruction(task: ai_task.GenDataTask) -> str:
    if not task.structure:
        return ""

    field_names = [str(key) for key in task.structure.schema]
    if not field_names:
        return "Return valid JSON."

    fields = ", ".join(field_names)
    return (
        f"Return only valid JSON. The JSON object must contain these fields: {fields}."
    )
