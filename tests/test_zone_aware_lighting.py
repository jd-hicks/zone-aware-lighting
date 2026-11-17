"""Acceptance tests from docs/design.md §43 (plus invariant checks)."""
import pytest
from conftest import setup_automations, running, settle

PRE = {"preactivation_sensors": ["binary_sensor.boundary", "binary_sensor.door"]}
SLEEP_OFF = [{"condition": "state", "entity_id": "input_boolean.sleep", "state": "off"}]
NIGHT_ON = [{"condition": "state", "entity_id": "input_boolean.night", "state": "on"}]


async def test_01_traditional(hass, env):
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.pir", "off")
    await env.advance(178)
    assert env.state("light.main") == "on"
    await env.advance(3)
    assert env.state("light.main") == "off"
    assert running(hass) == 0


async def test_01b_zero_vacancy_timeout(hass, env):
    await setup_automations(hass, {"vacancy_timeout": 0})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.pir", "off")
    assert env.state("light.main") == "off"


async def test_02_multiple_occupancy(hass, env):
    await setup_automations(hass, {"occupancy_sensors": ["binary_sensor.pir", "binary_sensor.mmwave"]})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.mmwave", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(600)
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.mmwave", "off")
    await env.advance(178)
    assert env.state("light.main") == "on"
    await env.advance(3)
    assert env.state("light.main") == "off"


async def test_02b_second_occupancy_sensor_can_activate(hass, env):
    await setup_automations(hass, {"occupancy_sensors": ["binary_sensor.pir", "binary_sensor.mmwave"]})
    await env.step("binary_sensor.mmwave", "on")
    assert env.state("light.main") == "on"


async def test_03_brief_false_negative(hass, env):
    await setup_automations(hass, {"occupancy_sensors": ["binary_sensor.pir", "binary_sensor.mmwave"]})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(100)
    await env.step("binary_sensor.mmwave", "on")
    await env.advance(300)
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.mmwave", "off")
    await env.advance(150)
    assert env.state("light.main") == "on"  # timer restarted, not resumed
    await env.advance(35)
    assert env.state("light.main") == "off"
    assert len(env.offs("light.main")) == 1


async def test_04_retention_cannot_activate(hass, env):
    await setup_automations(hass, {"additional_retention_sensors": ["binary_sensor.ret"]})
    await env.step("binary_sensor.ret", "on")
    await env.advance(30)
    assert env.state("light.main") == "off"
    assert running(hass) == 0
    assert env.calls == []


async def test_04b_retention_extends_session(hass, env):
    await setup_automations(hass, {"additional_retention_sensors": ["binary_sensor.ret"]})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.ret", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(1000)
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.ret", "off")
    await env.advance(181)
    assert env.state("light.main") == "off"


async def test_05_successful_preactivation(hass, env):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.main") == "on"
    await env.advance(5)
    await env.step("binary_sensor.pir", "on")
    await env.advance(30)
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.boundary", "off")
    await env.step("binary_sensor.pir", "off")
    await env.advance(178)
    assert env.state("light.main") == "on"
    await env.advance(3)
    assert env.state("light.main") == "off"
    assert len(env.offs("light.main")) == 1


async def test_06_failed_preactivation(hass, env):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.main") == "on"
    await env.advance(9)
    assert env.state("light.main") == "on"
    await env.advance(2)
    assert env.state("light.main") == "off"
    assert running(hass) == 0


async def test_06b_preactivation_is_edge_triggered(hass, env):
    """Staying on does not extend; a new off->on edge restarts the window."""
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")
    await env.advance(11)
    assert env.state("light.main") == "off"
    await env.advance(100)  # boundary still on: nothing happens
    assert env.state("light.main") == "off"
    await env.step("binary_sensor.boundary", "off")
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.main") == "on"
    await env.advance(6)
    await env.step("binary_sensor.boundary", "off")
    await env.step("binary_sensor.boundary", "on")  # refresh at ~t=7
    await env.advance(8)
    assert env.state("light.main") == "on"
    await env.advance(3)
    assert env.state("light.main") == "off"


async def test_07_retention_cannot_confirm(hass, env):
    await setup_automations(hass, {**PRE, "additional_retention_sensors": ["binary_sensor.ret"]})
    await env.step("binary_sensor.boundary", "on")
    await env.step("binary_sensor.ret", "on")
    await env.advance(11)
    assert env.state("light.main") == "off"
    assert running(hass) == 0


async def test_08_door_preactivation(hass, env):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.door", "on")
    assert env.state("light.main") == "on"
    await env.advance(11)
    assert env.state("light.main") == "off"
    await env.advance(600)
    assert env.state("light.main") == "off"
    assert env.state("binary_sensor.door") == "on"


async def test_08b_open_door_does_not_retain(hass, env):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.door", "on")
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(181)
    assert env.state("light.main") == "off"


async def test_09_two_people_adjacent_rooms(hass, env):
    await setup_automations(
        hass,
        {"occupancy_sensors": ["binary_sensor.pir_a"], "default_target": ["light.a"],
         "preactivation_sensors": ["binary_sensor.boundary"]},
        {"occupancy_sensors": ["binary_sensor.pir_b"], "default_target": ["light.b"],
         "preactivation_sensors": ["binary_sensor.boundary"]},
    )
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.a") == "on" and env.state("light.b") == "on"
    await env.step("binary_sensor.pir_a", "on")
    await env.step("binary_sensor.pir_b", "on")
    await env.advance(30)
    assert env.state("light.a") == "on" and env.state("light.b") == "on"
    await env.step("binary_sensor.pir_a", "off")
    await env.advance(181)
    assert env.state("light.a") == "off" and env.state("light.b") == "on"


async def test_10_shared_boundary_one_side_occupied(hass, env):
    await setup_automations(
        hass,
        {"occupancy_sensors": ["binary_sensor.pir_a"], "default_target": ["light.a"],
         "preactivation_sensors": ["binary_sensor.boundary"]},
        {"occupancy_sensors": ["binary_sensor.pir_b"], "default_target": ["light.b"],
         "preactivation_sensors": ["binary_sensor.boundary"]},
    )
    await env.step("binary_sensor.pir_a", "on")
    assert env.state("light.a") == "on"
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.b") == "on"
    await env.advance(11)
    assert env.state("light.a") == "on"
    assert env.state("light.b") == "off"
    assert env.offs("light.a") == []


async def test_11_shared_boundary_both_vacant(hass, env):
    await setup_automations(
        hass,
        {"occupancy_sensors": ["binary_sensor.pir_a"], "default_target": ["light.a"],
         "preactivation_sensors": ["binary_sensor.boundary"]},
        {"occupancy_sensors": ["binary_sensor.pir_b"], "default_target": ["light.b"],
         "preactivation_sensors": ["binary_sensor.boundary"]},
    )
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.a") == "on" and env.state("light.b") == "on"
    await env.step("binary_sensor.pir_b", "on")
    await env.advance(11)
    assert env.state("light.b") == "on"
    assert env.state("light.a") == "off"


@pytest.mark.parametrize(
    ("agg", "threshold", "expected"),
    [
        ("minimum", 36, "on"), ("minimum", 35, "off"),
        ("maximum", 281, "on"), ("maximum", 280, "off"),
        ("average", 124, "on"), ("average", 123, "off"),
        ("median", 56, "on"), ("median", 55, "off"),
    ],
)
async def test_12_13_illuminance_aggregation(hass, env, agg, threshold, expected):
    env.set("sensor.lux_a", "35", {"device_class": "illuminance"})
    env.set("sensor.lux_b", "55", {"device_class": "illuminance"})
    env.set("sensor.lux_c", "280", {"device_class": "illuminance"})
    await setup_automations(hass, {
        "illuminance_sensors": ["sensor.lux_a", "sensor.lux_b", "sensor.lux_c"],
        "illuminance_aggregation": agg, "illuminance_threshold": threshold})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == expected
    assert running(hass) == 1  # occupancy session exists either way


async def test_13b_inhibited_session_later_request(hass, env):
    env.set("sensor.lux_a", "500", {"device_class": "illuminance"})
    await setup_automations(hass, {"illuminance_sensors": ["sensor.lux_a"]})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "off"
    env.set("sensor.lux_a", "10", {"device_class": "illuminance"})
    await env.step("binary_sensor.pir", "off")
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"


@pytest.mark.parametrize(("threshold", "expected"), [(51, "on"), (50, "off")])
async def test_14_partial_illuminance_failure(hass, env, threshold, expected):
    env.set("sensor.lux_a", "40", {"device_class": "illuminance"})
    env.set("sensor.lux_b", "unavailable", {"device_class": "illuminance"})
    env.set("sensor.lux_c", "60", {"device_class": "illuminance"})
    await setup_automations(hass, {
        "illuminance_sensors": ["sensor.lux_a", "sensor.lux_b", "sensor.lux_c"],
        "illuminance_threshold": threshold})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == expected


async def test_15_complete_illuminance_failure(hass, env):
    env.set("sensor.lux_a", "unknown", {"device_class": "illuminance"})
    env.set("sensor.lux_b", "unavailable", {"device_class": "illuminance"})
    await setup_automations(hass, {
        "illuminance_sensors": ["sensor.lux_a", "sensor.lux_b"], "illuminance_threshold": 1})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"


async def test_16_rising_illuminance_does_not_deactivate(hass, env):
    env.set("sensor.lux_a", "10", {"device_class": "illuminance"})
    await setup_automations(hass, {"illuminance_sensors": ["sensor.lux_a"]})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"
    await env.step("sensor.lux_a", "5000")
    await env.advance(600)
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_17_activation_condition(hass, env):
    await setup_automations(hass, {"activation_conditions": SLEEP_OFF})
    env.set("input_boolean.sleep", "on")
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "off"
    assert running(hass) == 1
    env.set("input_boolean.sleep", "off")
    await env.step()
    assert env.state("light.main") == "off"  # conditions are not triggers
    await env.step("binary_sensor.pir", "off")
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"


async def test_17b_condition_gates_preactivation(hass, env):
    await setup_automations(hass, {**PRE, "activation_conditions": SLEEP_OFF})
    env.set("input_boolean.sleep", "on")
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.main") == "off"
    assert running(hass) == 0
    env.set("input_boolean.sleep", "off")
    await env.step("binary_sensor.pir", "on")  # evaluated independently
    assert env.state("light.main") == "on"


@pytest.mark.parametrize(("night", "on_light", "off_light"),
                         [("on", "light.night", "light.main"), ("off", "light.main", "light.night")])
async def test_18_alternate_target(hass, env, night, on_light, off_light):
    await setup_automations(hass, {"alternate_target": ["light.night"],
                                   "alternate_target_conditions": NIGHT_ON})
    env.set("input_boolean.night", night)
    await env.step("binary_sensor.pir", "on")
    assert env.state(on_light) == "on"
    assert env.state(off_light) == "off"


async def test_19_global_conditions_compound(hass, env):
    await setup_automations(hass, {"activation_conditions": SLEEP_OFF,
                                   "alternate_target": ["light.night"],
                                   "alternate_target_conditions": NIGHT_ON})
    env.set("input_boolean.night", "on")
    env.set("input_boolean.sleep", "on")
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "off" and env.state("light.night") == "off"
    env.set("input_boolean.sleep", "off")
    await env.step("binary_sensor.pir", "off")
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.night") == "on" and env.state("light.main") == "off"


async def test_20_alternate_changes_during_occupancy(hass, env):
    await setup_automations(hass, {"alternate_target": ["light.night"],
                                   "alternate_target_conditions": NIGHT_ON})
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"
    env.set("input_boolean.night", "on")
    await env.step("binary_sensor.pir", "off")
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    assert env.state("light.main") == "on" and env.state("light.night") == "off"
    await env.advance(181)
    assert env.state("light.main") == "off"
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.night") == "on" and env.state("light.main") == "off"


async def test_21_manual_light_survives_failed_preactivation(hass, env):
    await setup_automations(hass, PRE)
    env.set("light.main", "on")
    await env.step("binary_sensor.boundary", "on")
    await env.advance(30)
    assert env.state("light.main") == "on"
    assert env.calls == []


async def test_21b_partial_ownership(hass, env):
    await setup_automations(hass, {**PRE, "default_target": ["light.main", "light.extra"]})
    env.set("light.main", "on")
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.extra") == "on"
    await env.advance(11)
    assert env.state("light.extra") == "off"
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_22_unavailable_blocks_vacancy(hass, env):
    await setup_automations(hass, {"occupancy_sensors": ["binary_sensor.pir", "binary_sensor.mmwave"]})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.mmwave", "unavailable")
    await env.step("binary_sensor.pir", "off")
    await env.advance(1000)
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.mmwave", "unknown")
    await env.advance(1000)
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.mmwave", "off")
    await env.advance(181)
    assert env.state("light.main") == "off"


async def test_22b_unavailable_retention_blocks_vacancy(hass, env):
    await setup_automations(hass, {"additional_retention_sensors": ["binary_sensor.ret"]})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.ret", "unavailable")
    await env.step("binary_sensor.pir", "off")
    await env.advance(1000)
    assert env.state("light.main") == "on"


async def _same_tick(env, entity_id, seconds):
    """Change a sensor and expire the timer in the same loop tick (no settle)."""
    from datetime import timedelta
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    env.set(entity_id, "on")
    env.freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(env.hass)
    await env.advance(5)


async def test_23_occupancy_wins_vacancy_race(hass, env):
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(178)
    await _same_tick(env, "binary_sensor.pir", 3)
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_23a_retention_wins_vacancy_race(hass, env):
    await setup_automations(hass, {"additional_retention_sensors": ["binary_sensor.ret"]})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(178)
    await _same_tick(env, "binary_sensor.ret", 3)
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_23b_occupancy_wins_preactivation_race(hass, env):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")
    await env.advance(8)
    await _same_tick(env, "binary_sensor.pir", 3)
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_23c_dropped_trigger_during_shutdown_recovers(hass, env):
    """Occupancy turning on while the turn-off is in flight (trigger ignored)."""
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    env.on_turn_off = lambda: env.set("binary_sensor.pir", "on")
    await env.advance(181)
    env.on_turn_off = None
    assert env.state("light.main") == "on"
    assert running(hass) == 1


@pytest.mark.parametrize("provisional", [False, True])
@pytest.mark.parametrize("gate", ["conditions", "illuminance"])
@pytest.mark.parametrize("alternate", [False, True])
async def test_23f_shutdown_restores_only_affected_lights(hass, env, provisional, gate, alternate):
    target = "light.night" if alternate else "light.main"
    inputs = {
        **PRE,
        "default_target": ["light.main", "light.extra"],
        "activation_conditions": SLEEP_OFF,
        "illuminance_sensors": ["sensor.lux_a"],
        "alternate_target": ["light.night", "light.extra"] if alternate else [],
        "alternate_target_conditions": NIGHT_ON,
    }
    env.set("sensor.lux_a", "10", {"device_class": "illuminance"})
    env.set("input_boolean.night", "on")
    await setup_automations(hass, inputs)
    if provisional:
        await env.step("binary_sensor.boundary", "on")
    else:
        await env.step("binary_sensor.pir", "on")
        await env.step("binary_sensor.pir", "off")
    assert env.state(target) == "on"
    await env.step("light.extra", "off")
    await env.step("input_boolean.night", "off")
    if gate == "conditions":
        await env.step("input_boolean.sleep", "on")
    else:
        await env.step("sensor.lux_a", "500")
    env.calls.clear()
    env.on_turn_off = lambda: env.set("binary_sensor.pir", "on")
    await env.advance(11 if provisional else 181)
    env.on_turn_off = None
    assert env.state(target) == "on"
    assert env.state("light.extra") == "off"
    assert env.state("light.main" if alternate else "light.night") == "off"
    assert env.calls == [("off", target), ("on", target)]
    assert running(hass) == 1
    await env.step("binary_sensor.pir", "off")
    await env.advance(181)
    assert env.state(target) == "off"
    assert running(hass) == 0


@pytest.mark.parametrize("state", ["on", "unknown", "unavailable"])
async def test_23g_retention_during_shutdown_restores_session(hass, env, state):
    await setup_automations(hass, {
        "additional_retention_sensors": ["binary_sensor.ret"],
        "activation_conditions": SLEEP_OFF,
    })
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.step("input_boolean.sleep", "on")
    env.on_turn_off = lambda: env.set("binary_sensor.ret", state)
    await env.advance(181)
    env.on_turn_off = None
    assert env.state("light.main") == "on"
    assert running(hass) == 1
    await env.step("binary_sensor.ret", "off")
    await env.advance(181)
    assert env.state("light.main") == "off"


async def test_23h_retention_during_withdrawal_cannot_confirm(hass, env):
    await setup_automations(hass, {
        **PRE, "additional_retention_sensors": ["binary_sensor.ret"],
    })
    await env.step("binary_sensor.boundary", "on")
    env.on_turn_off = lambda: env.set("binary_sensor.ret", "on")
    await env.advance(11)
    env.on_turn_off = None
    assert env.state("light.main") == "off"
    assert running(hass) == 0


@pytest.mark.parametrize("provisional", [False, True])
@pytest.mark.parametrize("entity_id", ["binary_sensor.pir", "binary_sensor.ret"])
async def test_23i_recheck_after_shutdown_preparation(hass, env, monkeypatch, provisional, entity_id):
    from homeassistant.helpers import script as script_mod
    original = script_mod._ScriptRun._async_step_variables
    fired = []

    async def inject_before_dispatch(self):
        await original(self)
        if not fired and self._variables.get("finished") and self._variables.get("lights_to_turn_off"):
            fired.append(True)
            env.set(entity_id, "on")

    monkeypatch.setattr(script_mod._ScriptRun, "_async_step_variables", inject_before_dispatch)
    await setup_automations(hass, {
        **PRE, "additional_retention_sensors": ["binary_sensor.ret"],
    })
    if provisional:
        await env.step("binary_sensor.boundary", "on")
    else:
        await env.step("binary_sensor.pir", "on")
        await env.step("binary_sensor.pir", "off")
    await env.advance(11 if provisional else 181)
    assert fired
    if provisional and entity_id == "binary_sensor.ret":
        assert env.state("light.main") == "off"
        assert running(hass) == 0
    else:
        assert env.state("light.main") == "on"
        assert env.offs("light.main") == []
        assert running(hass) == 1


@pytest.mark.parametrize("confirmed", [False, True])
async def test_manual_off_on_does_not_end_session(hass, env, confirmed):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")
    if confirmed:
        await env.step("binary_sensor.pir", "on")
    await env.step("light.main", "off")
    assert running(hass) == 1
    await env.step("light.main", "on")
    assert running(hass) == 1
    if confirmed:
        await env.step("binary_sensor.pir", "off")
    await env.advance(181 if confirmed else 11)
    assert env.state("light.main") == "off"
    assert running(hass) == 0


async def test_session_reactivates_manually_switched_off_target(hass, env):
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", "on")
    await env.step("light.main", "off")  # user switches off mid-session
    await env.advance(5)
    assert env.state("light.main") == "off"  # stale edge is not a new request
    await env.step("binary_sensor.pir", "off")
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"


async def test_occupied_session_ignores_preactivation(hass, env):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.boundary", "on")
    await env.advance(30)
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_24_run_cancelled_mid_provisional_is_safe(hass, env):
    """Approximates restart/reload: the run is cancelled; nothing is shut down."""
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")  # provisional
    assert env.state("light.main") == "on"
    for svc in ("turn_off", "turn_on"):
        await hass.services.async_call("automation", svc,
                                       {"entity_id": "automation.zal_0"}, blocking=True)
    await env.advance(600)
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []
    # Next occupancy session recovers: claims the selected target, ends at vacancy.
    await env.step("binary_sensor.boundary", "off")
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(181)
    assert env.state("light.main") == "off"


async def test_24b_turning_automation_off_mid_vacancy(hass, env):
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(60)
    await hass.services.async_call("automation", "turn_off",
                                   {"entity_id": "automation.zal_0"}, blocking=True)
    await hass.services.async_call("automation", "turn_on",
                                   {"entity_id": "automation.zal_0"}, blocking=True)
    await env.advance(600)
    assert env.state("light.main") == "on"


@pytest.mark.parametrize("state", ["unknown", "unavailable"])
async def test_24c_sensor_recovery_to_on_activates(hass, env, state):
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", state)
    await env.step("binary_sensor.pir", "on")
    assert env.state("light.main") == "on"
    await env.step("binary_sensor.pir", "off")
    await env.advance(181)
    assert env.state("light.main") == "off"


@pytest.mark.parametrize("state", ["unknown", "unavailable"])
async def test_24d_preactivation_recovery_requires_off_to_on(hass, env, state):
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", state)
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.main") == "off"
    assert env.calls == []
    assert running(hass) == 0
    await env.step("binary_sensor.boundary", "off")
    await env.step("binary_sensor.boundary", "on")
    assert env.state("light.main") == "on"


def _inject_after_timeout(monkeypatch, env, step_name, entity_id):
    """Turn a sensor on after a wait step times out but before the next step.

    This is the only way to deterministically hit the window that the
    "recheck immediately before turn-off" logic protects. It patches private
    Home Assistant internals (homeassistant.helpers.script._ScriptRun), so if
    tests 23d/23e fail after an HA upgrade, check this helper before
    suspecting the blueprint. The `assert fired` in each test detects the
    case where the patch silently stops applying.
    """
    from homeassistant.helpers import script as script_mod
    original = getattr(script_mod._ScriptRun, step_name)
    fired = []

    async def wrapped(self):
        await original(self)
        if not fired and self._variables["wait"]["completed"] is False:
            fired.append(True)
            env.set(entity_id, "on")

    monkeypatch.setattr(script_mod._ScriptRun, step_name, wrapped)
    return fired


async def test_23d_recheck_before_vacancy_shutdown(hass, env, monkeypatch):
    fired = _inject_after_timeout(monkeypatch, env, "_async_step_wait_template", "binary_sensor.pir")
    await setup_automations(hass, {})
    await env.step("binary_sensor.pir", "on")
    await env.step("binary_sensor.pir", "off")
    await env.advance(185)
    assert fired
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []


async def test_23e_recheck_before_provisional_withdrawal(hass, env, monkeypatch):
    fired = _inject_after_timeout(monkeypatch, env, "_async_step_wait_for_trigger", "binary_sensor.pir")
    await setup_automations(hass, PRE)
    await env.step("binary_sensor.boundary", "on")
    await env.advance(15)
    assert fired
    assert env.state("light.main") == "on"
    assert env.offs("light.main") == []
