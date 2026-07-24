"""Config flow for Grouped Lights."""
from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class GroupedLightsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Grouped Lights (user step added in a later task)."""

    VERSION = 1
