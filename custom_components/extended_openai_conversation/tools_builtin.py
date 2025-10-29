from abc import ABC, abstractmethod
from datetime import timedelta
from functools import partial
import logging
import os
import re
import sqlite3
import time
from typing import Any, TYPE_CHECKING
from urllib import parse

try:
    from openai import AsyncAzureOpenAI, AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncAzureOpenAI = None  # type: ignore[assignment]
    AsyncOpenAI = None  # type: ignore[assignment]
import voluptuous as vol
import yaml

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

from homeassistant.components import (
    automation,
    conversation,
    energy,
    recorder,
    rest,
    scrape,
)
from homeassistant.components.automation.config import _async_validate_config_item
from homeassistant.components.script.config import SCRIPT_ENTITY_SCHEMA
from homeassistant.config import AUTOMATION_CONFIG_PATH
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_NAME,
    CONF_PARAMS,
    CONF_PAYLOAD,
    CONF_RESOURCE,
    CONF_RESOURCE_TEMPLATE,
    CONF_TIMEOUT,
    CONF_VALUE_TEMPLATE,
    CONF_VERIFY_SSL,
    SERVICE_RELOAD,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.script import Script
from homeassistant.helpers.template import Template
import homeassistant.util.dt as dt_util

from .const import CONF_PAYLOAD_TEMPLATE, DOMAIN, EVENT_AUTOMATION_REGISTERED
from .exceptions import (
    CallServiceError,
    EntityNotExposed,
    EntityNotFound,
    FunctionNotFound,
    InvalidFunction,
    NativeNotFound,
)

_LOGGER = logging.getLogger(__name__)


AZURE_DOMAIN_PATTERN = r"\.(openai\.azure\.com|azure-api\.net)"

HISTORY_SUMMARY_LIMIT = 10

# REST helper mirrors https://www.home-assistant.io/integrations/rest/ defaults.
REST_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
REST_BODY_MAX_CHARS = 8192
SCRAPE_SAFE_MAX_INDEX = 50


def _lazy_import_bs4():
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep
        raise HomeAssistantError(
            "beautifulsoup4 is required for the scrape tool but is not installed."
        ) from exc
    return BeautifulSoup


def get_function_executor(value: str):
    function_executor = FUNCTION_EXECUTORS.get(value)
    if function_executor is None:
        raise FunctionNotFound(value)
    return function_executor


def is_azure(base_url: str):
    if base_url and re.search(AZURE_DOMAIN_PATTERN, base_url):
        return True
    return False


def convert_to_template(
    settings,
    template_keys=["data", "event_data", "target", "service"],
    hass: HomeAssistant | None = None,
):
    _convert_to_template(settings, template_keys, hass, [])


def _convert_to_template(settings, template_keys, hass, parents: list[str]):
    if isinstance(settings, dict):
        for key, value in settings.items():
            if isinstance(value, str) and (
                key in template_keys or set(parents).intersection(template_keys)
            ):
                settings[key] = Template(value, hass)
            if isinstance(value, dict):
                parents.append(key)
                _convert_to_template(value, template_keys, hass, parents)
                parents.pop()
            if isinstance(value, list):
                parents.append(key)
                for item in value:
                    _convert_to_template(item, template_keys, hass, parents)
                parents.pop()
    if isinstance(settings, list):
        for setting in settings:
            _convert_to_template(setting, template_keys, hass, parents)


def _get_rest_data(hass, rest_config, arguments):
    rest_config.setdefault(CONF_METHOD, rest.const.DEFAULT_METHOD)
    rest_config.setdefault(CONF_VERIFY_SSL, rest.const.DEFAULT_VERIFY_SSL)
    rest_config.setdefault(CONF_TIMEOUT, rest.data.DEFAULT_TIMEOUT)
    rest_config.setdefault(rest.const.CONF_ENCODING, rest.const.DEFAULT_ENCODING)

    resource_template: Template | None = rest_config.get(CONF_RESOURCE_TEMPLATE)
    if resource_template is not None:
        rest_config.pop(CONF_RESOURCE_TEMPLATE)
        rest_config[CONF_RESOURCE] = resource_template.async_render(
            arguments, parse_result=False
        )

    payload_template: Template | None = rest_config.get(CONF_PAYLOAD_TEMPLATE)
    if payload_template is not None:
        rest_config.pop(CONF_PAYLOAD_TEMPLATE)
        rest_config[CONF_PAYLOAD] = payload_template.async_render(
            arguments, parse_result=False
        )

    return rest.create_rest_data_from_config(hass, rest_config)


async def validate_authentication(
    hass: HomeAssistant,
    api_key: str,
    base_url: str,
    api_version: str,
    organization: str = None,
    skip_authentication=False,
) -> None:
    if skip_authentication:
        return

    global AsyncAzureOpenAI, AsyncOpenAI

    if AsyncAzureOpenAI is None or AsyncOpenAI is None:
        from openai import AsyncAzureOpenAI as _AsyncAzureOpenAI, AsyncOpenAI as _AsyncOpenAI

        AsyncAzureOpenAI = _AsyncAzureOpenAI  # type: ignore[assignment]
        AsyncOpenAI = _AsyncOpenAI  # type: ignore[assignment]

    if is_azure(base_url):
        client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,
            api_version=api_version,
            organization=organization,
            http_client=get_async_client(hass),
        )
    else:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            http_client=get_async_client(hass),
        )

    await hass.async_add_executor_job(partial(client.models.list, timeout=10))


class FunctionExecutor(ABC):
    def __init__(self, data_schema=vol.Schema({})) -> None:
        """initialize function executor"""
        self.data_schema = data_schema.extend({vol.Required("type"): str})

    def to_arguments(self, arguments):
        """to_arguments function"""
        try:
            return self.data_schema(arguments)
        except vol.error.Error as e:
            function_type = next(
                (key for key, value in FUNCTION_EXECUTORS.items() if value == self),
                None,
            )
            raise InvalidFunction(function_type) from e

    def validate_entity_ids(self, hass: HomeAssistant, entity_ids, exposed_entities):
        if any(hass.states.get(entity_id) is None for entity_id in entity_ids):
            raise EntityNotFound(entity_ids)
        exposed_entity_ids = {exposed["entity_id"] for exposed in exposed_entities}
        missing = set(entity_ids) - exposed_entity_ids
        if missing:
            # Exposure follows Assist's 'conversation' assistant toggle (see
            # homeassistant.components.homeassistant.exposed_entities.async_should_expose).
            _LOGGER.debug(
                "Exposure denied for assistant='conversation', entities=%s",
                sorted(missing),
            )
            raise EntityNotExposed(sorted(missing))

    @abstractmethod
    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        """execute function"""


class NativeFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize native function"""
        super().__init__(vol.Schema({vol.Required("name"): str}))

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        name = function["name"]
        if name == "execute_service":
            return await self.execute_service(
                hass, function, arguments, user_input, exposed_entities
            )
        if name == "execute_service_single":
            return await self.execute_service_single(
                hass, function, arguments, user_input, exposed_entities
            )
        if name == "add_automation":
            return await self.add_automation(
                hass, function, arguments, user_input, exposed_entities
            )
        if name == "get_history":
            return await self.get_history(
                hass, function, arguments, user_input, exposed_entities
            )
        if name == "get_energy":
            return await self.get_energy(
                hass, function, arguments, user_input, exposed_entities
            )
        if name == "get_statistics":
            return await self.get_statistics(
                hass, function, arguments, user_input, exposed_entities
            )
        if name == "get_user_from_user_id":
            return await self.get_user_from_user_id(
                hass, function, arguments, user_input, exposed_entities
            )

        raise NativeNotFound(name)

    async def execute_service_single(
        self,
        hass: HomeAssistant,
        function,
        service_argument,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        domain = service_argument["domain"]
        service = service_argument["service"]
        service_data = service_argument.get(
            "service_data", service_argument.get("data", {})
        )
        entity_id = service_data.get("entity_id", service_argument.get("entity_id"))
        area_id = service_data.get("area_id")
        device_id = service_data.get("device_id")

        if isinstance(entity_id, str):
            entity_id = [e.strip() for e in entity_id.split(",")]
        service_data["entity_id"] = entity_id

        if entity_id is None and area_id is None and device_id is None:
            raise CallServiceError(domain, service, service_data)
        if not hass.services.has_service(domain, service):
            raise ServiceNotFound(domain, service)

        # If explicit entity_id is provided, validate exposure as usual and drop area/device
        self.validate_entity_ids(hass, entity_id or [], exposed_entities)
        if entity_id:
            # Avoid bypass via extra selectors
            service_data.pop("area_id", None)
            service_data.pop("device_id", None)

        # If no entity_id but area_id/device_id is provided, resolve targets and enforce exposure
        if not entity_id and (area_id or device_id):
            from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er  # lazy import
            from homeassistant.components.homeassistant.exposed_entities import async_should_expose

            def _as_list(x):
                if x is None:
                    return []
                if isinstance(x, list):
                    return x
                return [x]

            area_ids = [a for a in _as_list(area_id) if a]
            device_ids = [d for d in _as_list(device_id) if d]

            ent_reg = er.async_get(hass)
            dev_reg = dr.async_get(hass)
            targets: set[str] = set()

            # Resolve by device_id
            if device_ids:
                for entry in ent_reg.entities.values():
                    if entry.device_id and entry.device_id in device_ids:
                        targets.add(entry.entity_id)

            # Resolve by area_id (direct entity area or via device area)
            if area_ids:
                # Map device_id → area_id for quick lookups
                device_area = {dev.id: dev.area_id for dev in dev_reg.devices.values()}
                for entry in ent_reg.entities.values():
                    if entry.area_id and entry.area_id in area_ids:
                        targets.add(entry.entity_id)
                        continue
                    if entry.device_id and device_area.get(entry.device_id) in area_ids:
                        targets.add(entry.entity_id)

            # Filter to currently loaded entities only (avoid phantom registry entries)
            targets = {eid for eid in targets if hass.states.get(eid) is not None}

            hidden = [eid for eid in sorted(targets) if not async_should_expose(hass, "conversation", eid)]
            if hidden:
                _LOGGER.debug(
                    "Exposure denied for assistant='conversation', hidden targets=%s",
                    hidden,
                )
                return {"error": f"Some targets are hidden from Assist: {', '.join(hidden)}"}

            if not targets:
                return {"error": "No exposed targets found for the provided area/device"}

            if targets:
                # Limit the actual call to exposed targets only
                service_data = dict(service_data)
                service_data["entity_id"] = list(sorted(targets))
                # Avoid passing area/device ids to the call to prevent bypass
                service_data.pop("area_id", None)
                service_data.pop("device_id", None)

        try:
            await hass.services.async_call(
                domain=domain,
                service=service,
                service_data=service_data,
            )
            return {"success": True}
        except HomeAssistantError as e:
            _LOGGER.error(e)
            return {"error": str(e)}

    async def execute_service(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        result = []
        for service_argument in arguments.get("list", []):
            result.append(
                await self.execute_service_single(
                    hass, function, service_argument, user_input, exposed_entities
                )
            )
        return result

    async def add_automation(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        automation_config = yaml.safe_load(arguments["automation_config"])
        config = {"id": str(round(time.time() * 1000))}
        if isinstance(automation_config, list):
            config.update(automation_config[0])
        if isinstance(automation_config, dict):
            config.update(automation_config)

        await _async_validate_config_item(hass, config, True, False)

        automations = [config]
        with open(
            os.path.join(hass.config.config_dir, AUTOMATION_CONFIG_PATH),
            "r",
            encoding="utf-8",
        ) as f:
            current_automations = yaml.safe_load(f.read())

        with open(
            os.path.join(hass.config.config_dir, AUTOMATION_CONFIG_PATH),
            "a" if current_automations else "w",
            encoding="utf-8",
        ) as f:
            raw_config = yaml.dump(automations, allow_unicode=True, sort_keys=False)
            f.write("\n" + raw_config)

        await hass.services.async_call(automation.config.DOMAIN, SERVICE_RELOAD)
        hass.bus.async_fire(
            EVENT_AUTOMATION_REGISTERED,
            {"automation_config": config, "raw_config": raw_config},
        )
        return "Success"

    async def get_history(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        entity_ids = arguments.get("entity_ids", [])
        include_start_time_state = arguments.get("include_start_time_state", True)
        significant_changes_only = arguments.get("significant_changes_only", True)
        minimal_response = arguments.get("minimal_response", True)
        no_attributes = arguments.get("no_attributes", True)

        now = dt_util.utcnow()
        one_day = timedelta(days=1)
        start_time = self.as_utc(start_time, now - one_day, "start_time not valid")
        end_time = self.as_utc(end_time, start_time + one_day, "end_time not valid")

        self.validate_entity_ids(hass, entity_ids, exposed_entities)

        with recorder.util.session_scope(hass=hass, read_only=True) as session:
            result = await recorder.get_instance(hass).async_add_executor_job(
                recorder.history.get_significant_states_with_session,
                hass,
                session,
                start_time,
                end_time,
                entity_ids,
                None,
                include_start_time_state,
                significant_changes_only,
                minimal_response,
                no_attributes,
            )

        summary: list[dict[str, Any]] = []
        for entity_id, states in result.items():
            samples: list[dict[str, Any]] = []
            trimmed = list(states)[-HISTORY_SUMMARY_LIMIT:]
            for state in trimmed:
                if isinstance(state, State):
                    samples.append(
                        {
                            "last_changed": state.last_changed.isoformat(),
                            "state": state.state,
                            "attributes": None if no_attributes else dict(state.attributes),
                        }
                    )
                elif isinstance(state, dict):
                    samples.append(
                        {
                            "last_changed": state.get("last_changed"),
                            "state": state.get("state"),
                            "attributes": None if no_attributes else state.get("attributes"),
                        }
                    )
            summary.append({"entity_id": entity_id, "samples": samples})

        return summary

    async def get_energy(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        energy_manager: energy.data.EnergyManager = await energy.async_get_manager(hass)
        return energy_manager.data

    async def get_user_from_user_id(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        user = await hass.auth.async_get_user(user_input.context.user_id)
        return {'name': user.name if user and hasattr(user, 'name') else 'Unknown'}

    async def get_statistics(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        statistic_ids = arguments.get("statistic_ids", [])
        start_time = dt_util.as_utc(dt_util.parse_datetime(arguments["start_time"]))
        end_time = dt_util.as_utc(dt_util.parse_datetime(arguments["end_time"]))

        return await recorder.get_instance(hass).async_add_executor_job(
            recorder.statistics.statistics_during_period,
            hass,
            start_time,
            end_time,
            statistic_ids,
            arguments.get("period", "day"),
            arguments.get("units"),
            arguments.get("types", {"change"}),
        )

    def as_utc(self, value: str, default_value, parse_error_message: str):
        if value is None:
            return default_value

        parsed_datetime = dt_util.parse_datetime(value)
        if parsed_datetime is None:
            raise HomeAssistantError(parse_error_message)

        return dt_util.as_utc(parsed_datetime)

    def as_dict(self, state: State | dict[str, Any]):
        if isinstance(state, State):
            return state.as_dict()
        return state


class ScriptFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize script function"""
        super().__init__(SCRIPT_ENTITY_SCHEMA)

    def to_arguments(self, arguments):
        if "sequence" in arguments:
            return super().to_arguments(arguments)
        entity_id = arguments.get("entity_id")
        if isinstance(entity_id, str) and entity_id.startswith("script."):
            return {"type": arguments["type"], "entity_id": entity_id}
        raise InvalidFunction("script")

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        sequence = function.get("sequence") or arguments.get("sequence")
        if sequence:
            if not isinstance(sequence, list):
                raise HomeAssistantError("Script sequence must be a list of steps.")
            script = Script(
                hass,
                sequence,
                "extended_openai_conversation",
                DOMAIN,
                running_description="[extended_openai_conversation] function",
                logger=_LOGGER,
            )
            result = await script.async_run(
                run_variables=arguments, context=user_input.context
            )
            return result.variables.get("_function_result", "Success")

        entity_id = arguments.get("entity_id")
        if isinstance(entity_id, str) and entity_id.startswith("script."):
            domain, service = entity_id.split(".", 1)
            # Execute script entity as documented in
            # https://www.home-assistant.io/integrations/script/.
            await hass.services.async_call(
                domain,
                service,
                {"entity_id": entity_id},
                context=user_input.context,
            )
            return "Success"

        raise HomeAssistantError(
            "Script tool requires either a 'sequence' or script 'entity_id'."
        )


class TemplateFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize template function"""
        super().__init__(
            vol.Schema(
                {
                    vol.Required("value_template"): cv.template,
                    vol.Optional("parse_result"): bool,
                    # Accept variables mapping for render context
                    vol.Optional("vars", default={}): dict,
                }
            )
        )

    def to_arguments(self, arguments):
        """Normalize friendly keys before schema validation.

        Accepts 'template' → maps to 'value_template' and preserves optional 'vars'.
        Verified against HA template helper contract (cv.template + Template render).
        """
        mapped = dict(arguments)
        tmpl = mapped.get("value_template")
        if tmpl is None and isinstance(mapped.get("template"), str):
            mapped["value_template"] = mapped.pop("template")
        # Ensure vars is a dict if provided
        if "vars" in mapped and not isinstance(mapped["vars"], dict):
            raise vol.Invalid("vars must be a mapping")
        return self.data_schema(mapped)

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        value_template: Template | None = function.get("value_template") or arguments.get("value_template")
        if value_template is None:
            template_str = arguments.get("template")
            if not isinstance(template_str, str) or not template_str.strip():
                raise HomeAssistantError("Template tool requires a 'template' or 'value_template'")
            value_template = Template(template_str, hass)

        parse_result = function.get("parse_result", arguments.get("parse_json", False))
        # Merge provided vars mapping (function-level or call-level) into the context
        ctx_vars = {}
        if isinstance(function.get("vars"), dict):
            ctx_vars.update(function["vars"])
        if isinstance(arguments.get("vars"), dict):
            ctx_vars.update(arguments["vars"])
        # Render using HA template environment (async, non-blocking).
        # Pass all arguments as context plus optional 'vars'.
        merged_context = dict(arguments)
        if ctx_vars:
            merged_context.update(ctx_vars)
        return value_template.async_render(
            merged_context,
            parse_result=bool(parse_result),
        )


class RestFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize Rest function"""
        super().__init__(
            vol.Schema(rest.RESOURCE_SCHEMA).extend(
                {
                    vol.Optional("value_template"): cv.template,
                    vol.Optional("payload_template"): cv.template,
                }
            )
        )

    def to_arguments(self, arguments):
        """Normalize friendly keys (url, method, headers, params, timeout, body).

        Map to REST data schema (resource, method, headers, params, timeout, payload).
        Enforce http/https and request method allowlist including DELETE.
        See HA REST integration docs for RESOURCE_SCHEMA fields.
        """
        mapped = dict(arguments)
        # url → resource
        url = mapped.pop("url", mapped.get(CONF_RESOURCE))
        if url is None:
            raise vol.Invalid("REST tool requires a 'url' (http/https)")
        if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
            raise vol.Invalid("REST tool requires a 'url' (http/https)")
        mapped[CONF_RESOURCE] = url

        # method allowlist (include DELETE)
        method = str(mapped.pop("method", mapped.get(CONF_METHOD, "GET"))).upper()
        # HA rest.RESOURCE_SCHEMA restricts methods to rest.const.METHODS (POST/GET)
        # https://github.com/home-assistant/core/blob/dev/homeassistant/components/rest/schema.py
        if method not in {"GET", "POST"}:
            raise vol.Invalid("REST method not allowed")
        mapped[CONF_METHOD] = method

        # headers
        if "headers" in mapped:
            if not isinstance(mapped["headers"], dict):
                raise vol.Invalid("headers must be an object")
            mapped[CONF_HEADERS] = mapped.pop("headers")

        # params
        if "params" in mapped:
            if not isinstance(mapped["params"], dict):
                raise vol.Invalid("params must be an object")
            mapped[CONF_PARAMS] = {str(k): str(v) for k, v in mapped["params"].items()}
            mapped.pop("params", None)

        # timeout
        if "timeout" in mapped:
            try:
                mapped[CONF_TIMEOUT] = int(mapped.pop("timeout"))
            except Exception as exc:
                raise vol.Invalid("timeout must be an integer") from exc

        # body → payload (cap also enforced in execute)
        if "body" in mapped and CONF_PAYLOAD not in mapped:
            mapped[CONF_PAYLOAD] = str(mapped.pop("body"))

        return self.data_schema(mapped)

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        config = dict(function)

        # Merge normalized arguments from to_arguments into config
        for key in (CONF_RESOURCE, CONF_METHOD, CONF_HEADERS, CONF_PARAMS, CONF_TIMEOUT, CONF_VERIFY_SSL, CONF_PAYLOAD):
            if key in arguments:
                config[key] = arguments[key]

        request_url = arguments.get("url") or arguments.get(CONF_RESOURCE)
        if request_url:
            if not isinstance(request_url, str) or not request_url.lower().startswith(
                ("http://", "https://")
            ):
                raise HomeAssistantError("REST tool requires an http(s) URL.")
            config[CONF_RESOURCE] = request_url
        if CONF_RESOURCE not in config:
            raise HomeAssistantError("REST tool requires a 'url' argument.")

        method = str(arguments.get("method", config.get(CONF_METHOD, "GET"))).upper()
        if method not in REST_ALLOWED_METHODS:
            raise HomeAssistantError(
                f"REST method '{method}' is not allowed; "
                f"allowed methods: {', '.join(sorted(REST_ALLOWED_METHODS))}"
            )
        config[CONF_METHOD] = method

        # Prefer normalized CONF_HEADERS set by to_arguments
        headers = arguments.get(CONF_HEADERS) or arguments.get("headers")
        if headers is not None:
            if not isinstance(headers, dict):
                raise HomeAssistantError("REST headers must be an object of strings.")
            safe_headers: dict[str, str] = {str(k)[:64]: str(v)[:256] for k, v in headers.items()}
            config[CONF_HEADERS] = safe_headers

        # params
        if (CONF_PARAMS in arguments) or ("params" in arguments):
            params = arguments.get(CONF_PARAMS, arguments.get("params"))
            if not isinstance(params, dict):
                raise HomeAssistantError("REST params must be an object of strings.")
            config[CONF_PARAMS] = {str(k): str(v) for k, v in params.items()}

        if (payload := arguments.get("payload")) is not None:
            payload_str = str(payload)
            if len(payload_str) > REST_BODY_MAX_CHARS:
                raise HomeAssistantError("REST payload exceeds 8KB limit.")
            config[CONF_PAYLOAD] = payload_str

        # timeout
        if (CONF_TIMEOUT in arguments) or ("timeout" in arguments):
            try:
                config[CONF_TIMEOUT] = int(arguments.get(CONF_TIMEOUT, arguments.get("timeout")))
            except Exception as exc:
                raise HomeAssistantError("timeout must be an integer") from exc
        else:
            config.setdefault(CONF_TIMEOUT, min(15, config.get(CONF_TIMEOUT, 10)))
        config.setdefault(CONF_VERIFY_SSL, True)

        # REST helper mirrors https://www.home-assistant.io/integrations/rest/
        # behaviour: build data coordinator and read text/JSON.
        # Scrape helper aligns with https://www.home-assistant.io/integrations/scrape/
        # by delegating to the shared REST data coordinator.
        rest_data = _get_rest_data(hass, config, arguments)

        await rest_data.async_update()
        value = rest_data.data_without_xml()
        value_template = config.get(CONF_VALUE_TEMPLATE)

        if value is not None and value_template is not None:
            value = value_template.async_render_with_possible_json_value(
                value, None, arguments
            )

        return value


class ScrapeFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize Scrape function"""
        super().__init__(
            scrape.COMBINED_SCHEMA.extend(
                {
                    vol.Optional("value_template"): cv.template,
                    vol.Optional("payload_template"): cv.template,
                }
            )
        )

    def to_arguments(self, arguments):
        """Normalize friendly keys (url, select, attr, index) to COMBINED_SCHEMA.

        Friendly keys are mapped before validation so LLM calls don't fail early.
        Verified against HA scrape integration (selector/attribute/index semantics).
        """
        mapped = dict(arguments)
        # url → resource
        url = mapped.pop("url", mapped.get(CONF_RESOURCE))
        if url is None:
            raise vol.Invalid("Scrape tool requires a 'url'")
        if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
            raise vol.Invalid("Scrape tool requires a 'url' (http/https)")
        mapped[CONF_RESOURCE] = url

        # Build sensor list from friendly keys if absent
        if "sensor" not in mapped:
            select = mapped.pop("select", None)
            if not isinstance(select, str) or not select.strip():
                raise vol.Invalid("Scrape tool requires a 'select' CSS selector")
            idx = mapped.pop("index", 0)
            try:
                idx = int(idx)
            except Exception as exc:
                raise vol.Invalid("index must be an integer") from exc
            idx = max(0, min(idx, SCRAPE_SAFE_MAX_INDEX))
            sensor_cfg = {
                scrape.const.CONF_SELECT: select.strip(),
                scrape.const.CONF_INDEX: idx,
            }
            attr = mapped.pop("attr", mapped.pop("attribute", None))
            if attr is not None:
                sensor_cfg[CONF_ATTRIBUTE] = str(attr)
            mapped["sensor"] = [sensor_cfg]

        return self.data_schema(mapped)

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        _lazy_import_bs4()
        config = dict(function)

        request_url = arguments.get("url") or arguments.get(CONF_RESOURCE)
        if request_url:
            if not isinstance(request_url, str) or not request_url.lower().startswith(
                ("http://", "https://")
            ):
                raise HomeAssistantError("Scrape tool requires an http(s) URL.")
            config[CONF_RESOURCE] = request_url
        if CONF_RESOURCE not in config:
            raise HomeAssistantError("Scrape tool requires a 'url' argument.")

        sensor_configs = [dict(sensor) for sensor in config.get("sensor", [])]
        # Prefer normalized sensors from to_arguments if present
        if not sensor_configs and isinstance(arguments.get("sensor"), list):
            sensor_configs = [dict(s) for s in arguments["sensor"]]
        def _coerce_index(value: Any) -> int:
            if value in (None, ""):
                return 0
            try:
                parsed = int(value)
            except (TypeError, ValueError) as exc:
                raise HomeAssistantError("Scrape index must be an integer.") from exc
            return max(0, min(parsed, SCRAPE_SAFE_MAX_INDEX))

        if not sensor_configs:
            select = arguments.get("select")
            if not isinstance(select, str) or not select.strip():
                raise HomeAssistantError("Scrape tool requires a 'select' CSS selector.")
            sensor_config: dict[str, Any] = {
                scrape.const.CONF_SELECT: select.strip(),
                scrape.const.CONF_INDEX: _coerce_index(arguments.get("index")),
            }
            if attribute := arguments.get("attribute"):
                sensor_config[CONF_ATTRIBUTE] = str(attribute)
            sensor_configs = [sensor_config]
        else:
            select = arguments.get("select")
            index = arguments.get("index")
            attribute = arguments.get("attribute")
            target_sensor = sensor_configs[0]
            if select:
                target_sensor[scrape.const.CONF_SELECT] = str(select)
            if index is not None:
                target_sensor[scrape.const.CONF_INDEX] = _coerce_index(index)
            if attribute is not None:
                if attribute == "":
                    target_sensor.pop(CONF_ATTRIBUTE, None)
                else:
                    target_sensor[CONF_ATTRIBUTE] = str(attribute)
        config["sensor"] = sensor_configs

        rest_data = _get_rest_data(hass, config, arguments)
        coordinator = scrape.coordinator.ScrapeCoordinator(
            hass,
            rest_data,
            scrape.const.DEFAULT_SCAN_INTERVAL,
        )
        await coordinator.async_config_entry_first_refresh()

        new_arguments = dict(arguments)

        for sensor_config in config["sensor"]:
            name: Template = sensor_config.get(CONF_NAME)
            value = self._async_update_from_rest_data(
                coordinator.data, sensor_config, arguments
            )
            new_arguments["value"] = value
            if name:
                new_arguments[name.async_render()] = value

        result = new_arguments["value"]
        value_template = config.get(CONF_VALUE_TEMPLATE)

        if value_template is not None:
            result = value_template.async_render_with_possible_json_value(
                result, None, new_arguments
            )

        return result

    def _async_update_from_rest_data(
        self,
        data: Any,
        sensor_config: dict[str, Any],
        arguments: dict[str, Any],
    ) -> None:
        """Update state from the rest data."""
        value = self._extract_value(data, sensor_config)
        value_template = sensor_config.get(CONF_VALUE_TEMPLATE)

        if value_template is not None:
            value = value_template.async_render_with_possible_json_value(
                value, None, arguments
            )

        return value

    def _extract_value(self, data: Any, sensor_config: dict[str, Any]) -> Any:
        """Parse the html extraction in the executor."""
        value: str | list[str] | None
        select = sensor_config[scrape.const.CONF_SELECT]
        index = sensor_config.get(scrape.const.CONF_INDEX, 0)
        attr = sensor_config.get(CONF_ATTRIBUTE)
        try:
            if attr is not None:
                value = data.select(select)[index][attr]
            else:
                tag = data.select(select)[index]
                if tag.name in ("style", "script", "template"):
                    value = tag.string
                else:
                    value = tag.text
        except IndexError:
            _LOGGER.warning("Index '%s' not found", index)
            value = None
        except KeyError:
            _LOGGER.warning("Attribute '%s' not found", attr)
            value = None
        _LOGGER.debug("Parsed value: %s", value)
        return value


class CompositeFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize composite function"""
        super().__init__(
            vol.Schema(
                {
                    vol.Required("sequence"): vol.All(
                        cv.ensure_list, [self.function_schema]
                    )
                }
            )
        )

    def function_schema(self, value: Any) -> dict:
        """Validate a composite function schema."""
        if not isinstance(value, dict):
            raise vol.Invalid("expected dictionary")

        composite_schema = {vol.Optional("response_variable"): str}
        function_executor = get_function_executor(value["type"])

        return function_executor.data_schema.extend(composite_schema)(value)

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        config = function
        sequence = config.get("sequence") or arguments.get("sequence")
        if not isinstance(sequence, list) or not sequence:
            raise HomeAssistantError(
                "Composite tool requires a non-empty 'sequence' list."
            )

        for executor_config in sequence:
            function_executor = get_function_executor(executor_config["type"])
            result = await function_executor.execute(
                hass, executor_config, arguments, user_input, exposed_entities
            )

            response_variable = executor_config.get("response_variable")
            if response_variable:
                arguments[response_variable] = result

        return result


class SqliteFunctionExecutor(FunctionExecutor):
    def __init__(self) -> None:
        """initialize sqlite function"""
        super().__init__(
            vol.Schema(
                {
                    vol.Optional("query"): str,
                    vol.Optional("db_url"): str,
                    vol.Optional("single"): bool,
                }
            )
        )

    def is_exposed(self, entity_id, exposed_entities) -> bool:
        return any(
            exposed_entity["entity_id"] == entity_id
            for exposed_entity in exposed_entities
        )

    def is_exposed_entity_in_query(self, query: str, exposed_entities) -> bool:
        exposed_entity_ids = list(
            map(lambda e: f"'{e['entity_id']}'", exposed_entities)
        )
        return any(
            exposed_entity_id in query for exposed_entity_id in exposed_entity_ids
        )

    def raise_error(self, msg="Unexpected error occurred."):
        raise HomeAssistantError(msg)

    def get_default_db_url(self, hass: HomeAssistant) -> str:
        db_file_path = os.path.join(hass.config.config_dir, recorder.DEFAULT_DB_FILE)
        return f"file:{db_file_path}?mode=ro"

    def set_url_read_only(self, url: str) -> str:
        scheme, netloc, path, query_string, fragment = parse.urlsplit(url)
        query_params = parse.parse_qs(query_string)

        query_params["mode"] = ["ro"]
        new_query_string = parse.urlencode(query_params, doseq=True)

        return parse.urlunsplit((scheme, netloc, path, new_query_string, fragment))

    async def execute(
        self,
        hass: HomeAssistant,
        function,
        arguments,
        user_input: conversation.ConversationInput,
        exposed_entities,
    ):
        db_url = self.set_url_read_only(
            function.get("db_url", self.get_default_db_url(hass))
        )
        query = function.get("query", "{{query}}")

        template_arguments = {
            "is_exposed": lambda e: self.is_exposed(e, exposed_entities),
            "is_exposed_entity_in_query": lambda q: self.is_exposed_entity_in_query(
                q, exposed_entities
            ),
            "exposed_entities": exposed_entities,
            "raise": self.raise_error,
        }
        template_arguments.update(arguments)

        q = Template(query, hass).async_render(template_arguments)
        _LOGGER.debug("Rendered query: %s", q)

        with sqlite3.connect(db_url, uri=True) as conn:
            cursor = conn.cursor().execute(q)
            names = [description[0] for description in cursor.description]

            if function.get("single") is True:
                row = cursor.fetchone()
                return {name: val for name, val in zip(names, row)}

            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({name: val for name, val in zip(names, row)})
            return result


FUNCTION_EXECUTORS: dict[str, FunctionExecutor] = {
    "native": NativeFunctionExecutor(),
    "script": ScriptFunctionExecutor(),
    "template": TemplateFunctionExecutor(),
    "rest": RestFunctionExecutor(),
    "scrape": ScrapeFunctionExecutor(),
    "composite": CompositeFunctionExecutor(),
    "sqlite": SqliteFunctionExecutor(),
}
