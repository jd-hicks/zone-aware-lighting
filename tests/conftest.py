"""Harness: run zone_aware_lighting.yaml inside a real Home Assistant core.

Sensors are plain state objects and light services are mocks that record
calls and update state, so each test controls every input exactly.
"""
import asyncio
import os
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_fire_time_changed

# ZAL_BLUEPRINT may point at an alternate copy (e.g. to mutation-test a change).
BLUEPRINT = Path(
    os.environ.get(
        "ZAL_BLUEPRINT",
        Path(__file__).resolve().parents[1] / "zone_aware_lighting.yaml",
    )
)

SENSORS = {
    "binary_sensor.pir": "motion",
    "binary_sensor.mmwave": "occupancy",
    "binary_sensor.ret": "occupancy",
    "binary_sensor.boundary": "motion",
    "binary_sensor.door": "door",
    "binary_sensor.pir_a": "motion",
    "binary_sensor.pir_b": "motion",
}
LIGHTS = ["light.main", "light.night", "light.extra", "light.a", "light.b"]


async def settle(hass):
    """Let callbacks/service calls run without waiting for long automation runs.

    hass.async_block_till_done() cannot be used: a session is one long-running
    automation run that only ends at vacancy, so it would block forever.
    """
    for _ in range(30):
        await asyncio.sleep(0)


class Env:
    def __init__(self, hass, freezer):
        self.hass = hass
        self.freezer = freezer
        self.calls: list[tuple[str, str]] = []
        self.on_turn_off = None

    def set(self, entity_id, state, attrs=None):
        if attrs is None and entity_id in SENSORS:
            attrs = {"device_class": SENSORS[entity_id]}
        self.hass.states.async_set(entity_id, state, attrs or {})

    async def step(self, entity_id=None, state=None, wait=0.5):
        """Advance time a little, optionally change a state, settle."""
        self.freezer.tick(timedelta(seconds=wait))
        async_fire_time_changed(self.hass)
        await settle(self.hass)
        if entity_id:
            self.set(entity_id, state)
            await settle(self.hass)

    async def advance(self, seconds, chunk=1.0):
        remaining = seconds
        while remaining > 0:
            d = min(chunk, remaining)
            self.freezer.tick(timedelta(seconds=d))
            async_fire_time_changed(self.hass)
            await settle(self.hass)
            remaining -= d

    def state(self, entity_id):
        return self.hass.states.get(entity_id).state

    def offs(self, entity_id):
        return [c for c in self.calls if c == ("off", entity_id)]

    def ons(self, entity_id):
        return [c for c in self.calls if c == ("on", entity_id)]


@pytest.fixture
async def env(hass: HomeAssistant, tmp_path, freezer):
    freezer.move_to("2026-11-16 12:00:00+00:00")
    hass.config.config_dir = str(tmp_path)
    dst = tmp_path / "blueprints" / "automation" / "zal"
    dst.mkdir(parents=True)
    shutil.copy(BLUEPRINT, dst / "zone_aware_lighting.yaml")
    e = Env(hass, freezer)

    def ids(call: ServiceCall):
        v = call.data.get("entity_id", [])
        return [v] if isinstance(v, str) else list(v)

    async def turn_on(call):
        for i in ids(call):
            e.calls.append(("on", i))
            hass.states.async_set(i, "on")

    async def turn_off(call):
        for i in ids(call):
            e.calls.append(("off", i))
            hass.states.async_set(i, "off")
        if e.on_turn_off:
            e.on_turn_off()

    hass.services.async_register("light", "turn_on", turn_on)
    hass.services.async_register("light", "turn_off", turn_off)
    for s in SENSORS:
        e.set(s, "off")
    for light in LIGHTS:
        e.set(light, "off")
    for b in ("input_boolean.sleep", "input_boolean.night"):
        e.set(b, "off")
    for lx in ("sensor.lux_a", "sensor.lux_b", "sensor.lux_c"):
        e.set(lx, "unavailable", {"device_class": "illuminance"})
    await hass.async_block_till_done()
    return e


async def setup_automations(hass, *inputs_list):
    automations = []
    for n, inputs in enumerate(inputs_list):
        base = {
            "occupancy_sensors": ["binary_sensor.pir"],
            "default_target": ["light.main"],
        }
        base.update(inputs)
        automations.append(
            {
                "id": f"zal_{n}",
                "alias": f"zal {n}",
                "use_blueprint": {"path": "zal/zone_aware_lighting.yaml", "input": base},
            }
        )
    assert await async_setup_component(hass, "automation", {"automation": automations})
    await hass.async_block_till_done()
    for n in range(len(inputs_list)):
        st = hass.states.get(f"automation.zal_{n}")
        assert st is not None and st.state == "on", st


def running(hass, n=0):
    return hass.states.get(f"automation.zal_{n}").attributes.get("current", 0)
