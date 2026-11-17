# Zone-Aware Lighting: Design Specification

## Status

Initial design specification for Zone-Aware Lighting.

This document defines the intended behavior, scope, terminology, configuration model, and architectural constraints of the project. Implementation details may evolve, but the behavioral model described here should remain stable wherever practical.

---

# 1. Objective

Zone-Aware Lighting is a Home Assistant automation blueprint for occupancy-driven lighting.

It begins with the familiar motion-activated lighting model:

    motion detected
        -> light on

    motion clear
        -> wait
        -> light off

and progressively expands the detection aperture of the controlled lighting area.

Optional capabilities include:

- multiple occupancy sensors
- combining PIR motion and mmWave occupancy
- retention-only sensors
- preactivation from immediately adjacent transition areas
- preactivation from doors/openings
- multiple illuminance sensors
- illuminance aggregation
- additional Home Assistant activation conditions
- an optional alternate lighting target

The simplest useful configuration must remain approximately as simple as the standard Home Assistant motion-light blueprint.

Advanced features are additive.

---

# 2. Design Philosophy

## 2.1 Expand the Detection Aperture

Conventional motion lighting tends to assume:

    one sensor
        -> one light

Zone-Aware Lighting instead treats sensors as evidence relevant to a controlled lighting area.

The aperture can be expanded incrementally:

1. A single occupancy sensor provides conventional motion lighting.
2. Additional occupancy sensors broaden the evidence allowed to establish occupancy.
3. Additional retention sensors broaden the evidence allowed to maintain occupancy without gaining authority to activate lighting.
4. Preactivation sensors extend detection into immediately adjacent transition areas and boundaries.
5. Illuminance and additional conditions determine whether otherwise justified automatic activation should actually occur.
6. An optional alternate target allows the physical lighting source to change according to context without duplicating the occupancy automation.

No advanced feature should be required to obtain conventional motion-light behavior.

---

## 2.2 Positive Occupancy Evidence Is Stronger Than Negative Evidence

The blueprint should deliberately bias toward maintaining useful illumination.

For occupancy:

    ANY trusted occupancy sensor ON
        -> positive occupancy evidence

For vacancy:

    ALL occupancy sensors OFF
        AND
    ALL additional retention sensors OFF
        continuously for the vacancy timeout
        -> confirmed vacancy

This reflects the practical limitations of PIR and mmWave sensors.

A person may temporarily become invisible to one sensor while sitting still, watching television, working, or sleeping.

Therefore:

> Occupancy may be established quickly. Vacancy must be established conservatively.

---

## 2.3 Sensor Technology and Sensor Authority Are Separate Concepts

Zone-Aware Lighting should primarily care what authority a sensor has, not what physical technology produced it.

Examples:

    PIR motion
        -> occupancy

    mmWave occupancy
        -> occupancy

    mmWave with undesirable false activations
        -> additional retention

    narrowly aimed PIR at a room boundary
        -> preactivation

Sensor roles determine behavior.

---

## 2.4 Normalize Unusual Sensors Outside the Blueprint

Zone-Aware Lighting should consume standard Home Assistant Motion and Occupancy binary sensors.

The blueprint should not attempt to interpret arbitrary raw measurements.

For example:

    raw chair pressure
        -> Home Assistant template/helper
        -> binary_sensor.chair_occupied
        -> Zone-Aware Lighting

or:

    raw bed pressure
        -> device integration / template logic
        -> binary_sensor.bed_occupied
        -> Zone-Aware Lighting

The blueprint should not implement:

- arbitrary numeric thresholds for occupancy
- unit conversion
- pressure calibration
- per-device attribute interpretation
- state mappings
- arbitrary occupancy templates

Advanced users can normalize unusual hardware into a supported Home Assistant binary sensor first.

This preserves a clean architecture while retaining extensibility.

---

# 3. Terminology

## Controlled Lighting Area

The physical area whose lighting is managed by one blueprint automation instance.

Examples:

- bathroom
- laundry room
- bedroom
- hallway
- living room

Each automation instance owns its own lighting target or targets.

The term "area" here describes the physical lighting area and does not necessarily require use of a Home Assistant Area entity.

---

## Zone-Aware

"Zone" in the project name refers conceptually to the physical lighting zone governed by an automation instance.

It does NOT refer to a Home Assistant geographic Zone used for geofencing.

The blueprint should not create or depend on Home Assistant Zone entities.

---

## Occupancy

Strong evidence that someone is presently within the controlled lighting area.

---

## Retention

Evidence that is useful for preventing a currently occupied area from being declared vacant but is not trusted to establish occupancy by itself.

---

## Preactivation

Short-horizon, local evidence that someone may imminently enter the controlled lighting area.

Typical time horizon:

    seconds

rather than minutes.

Preactivation is provisional until confirmed by an occupancy sensor.

---

## Vacancy

The state reached after all occupancy and retention evidence has explicitly remained clear for the configured vacancy timeout.

---

# 4. Architectural Ownership

Each blueprint automation instance MUST control exactly one logical lighting area.

A sensor may be consumed by multiple independent automation instances.

An automation instance MUST NOT directly manipulate the lighting target owned by another room's automation.

For example:

    Vestibule PIR
        -> vestibule automation
        -> bathroom automation
        -> laundry automation

is valid.

But:

    bathroom occupied
        -> bathroom automation explicitly turns off laundry

is not valid.

Each controlled area independently evaluates its own evidence and controls its own lighting.

This allows simultaneous occupants in adjacent rooms without cross-automation interference.

---

# 5. Sensor Roles

The blueprint supports three sensor roles:

1. Occupancy Sensors
2. Additional Retention Sensors
3. Preactivation Sensors

Only Occupancy Sensors are required.

---

# 6. Occupancy Sensors

## Purpose

Occupancy Sensors are the primary trusted evidence that someone is within the controlled lighting area.

At least one occupancy sensor is required.

The input MUST support multiple entities.

Preferred Home Assistant binary sensor device classes:

- `motion`
- `occupancy`

The blueprint should use a filtered entity selector so configuration remains simple and inappropriate binary sensors are not displayed.

---

## Behavior

An Occupancy Sensor MAY:

- automatically activate lighting
- establish confirmed occupancy
- confirm provisional preactivation
- maintain confirmed occupancy
- cancel pending vacancy
- prevent shutdown

Semantics:

    ANY occupancy sensor ON
        -> confirmed occupancy

Any transition to `on`, including recovery from `unknown` or `unavailable`,
may establish occupancy. Unlike preactivation, occupancy does not require the
previous state to be `off`.

Occupancy sensors inherently participate in retention.

The user MUST NOT need to duplicate the same entity in another retention input.

---

## Examples

Traditional PIR:

    occupancy_sensors:
      - binary_sensor.hallway_motion

PIR plus mmWave:

    occupancy_sensors:
      - binary_sensor.living_room_motion
      - binary_sensor.living_room_occupancy

Bed occupancy may also qualify if the integration already exposes a normalized Occupancy binary sensor.

---

# 7. Additional Retention Sensors

## Purpose

Additional Retention Sensors provide useful positive evidence that someone may still occupy an already-confirmed lighting area, but they are deliberately given reduced authority.

This input is optional.

Preferred Home Assistant binary sensor device classes:

- `motion`
- `occupancy`

---

## Behavior

An Additional Retention Sensor MAY:

- prevent vacancy
- cancel pending vacancy shutdown
- extend an established occupancy session

An Additional Retention Sensor MUST NOT:

- activate lighting from vacancy
- establish occupancy from vacancy
- confirm preactivation
- convert provisional occupancy into confirmed occupancy

---

## Example

A PIR is reliable for activation, while an mmWave sensor occasionally detects activity outside the intended area.

Configure:

    occupancy_sensors:
      - binary_sensor.office_motion

    additional_retention_sensors:
      - binary_sensor.office_mmwave_occupancy

Behavior:

    PIR ON
        -> confirmed occupancy
        -> lighting may activate

    PIR OFF
    mmWave ON
        -> remain occupied

But:

    room vacant
    mmWave ON
        -> do NOT activate lighting

---

## Additional Retention as a Trust Boundary

Additional retention is intentionally positive-only evidence within an established occupancy session.

A useful interpretation is:

> This sensor is trustworthy enough to tell us not to turn the light off yet, but not trustworthy enough to tell us to turn the light on.

This distinction is particularly useful for mmWave devices with imperfect spatial boundaries.

---

# 8. Preactivation Sensors

## Purpose

Preactivation Sensors extend the detection perimeter of a lighting area.

They represent local, short-horizon transition evidence that someone may imminently enter the controlled lighting area.

This input is optional.

Supported binary sensor device classes SHOULD initially include:

- `motion`
- `door`
- `opening`

The implementation may include equivalent Home Assistant classes when required for compatibility, but should not broadly accept arbitrary binary sensors without a demonstrated use case.

---

## Preactivation Is Transition Evidence

Preactivation does not mean:

> Someone occupies this room.

It means:

> Something happened immediately adjacent to this area that makes occupancy likely within seconds.

Examples:

- vestibule PIR activates outside a bathroom
- narrow PIR detects someone crossing a bedroom/living-room boundary
- front door opens into an entry area
- interior door opens toward a controlled lighting area

---

## Preactivation Sequence

When a preactivation source transitions to its active state:

    preactivation event
        -> evaluate activation permission
        -> provisionally activate selected lighting target
        -> begin preactivation confirmation timeout

During the confirmation window:

    ANY Occupancy Sensor ON
        -> confirmed occupancy

If the timeout expires:

    recheck ALL Occupancy Sensors

If any Occupancy Sensor is ON:

    -> confirmed occupancy wins

If no Occupancy Sensor is ON:

    -> provisional activation is withdrawn

---

## Critical Preactivation Rule

Only Occupancy Sensors may confirm preactivation.

Additional Retention Sensors MUST NOT confirm preactivation.

Example:

    preactivation:
      vestibule motion

    occupancy:
      bathroom PIR

    retention:
      bathroom mmWave

Sequence:

    vestibule PIR ON
        -> bathroom provisionally illuminated

    bathroom mmWave ON
        -> does NOT confirm occupancy

    bathroom PIR never activates

    preactivation timeout expires
        -> provisional lighting withdrawn

But:

    vestibule PIR ON
        -> bathroom provisionally illuminated

    bathroom PIR ON
        -> confirmed occupancy

    bathroom mmWave may now help retain occupancy

This separation prevents an imprecise retention sensor from accidentally converting speculative lighting into established occupancy.

---

# 9. Preactivation Is Edge-Triggered

Preactivation sources are event-like.

For example:

    door CLOSED -> OPEN

or:

    motion CLEAR -> DETECTED

initiates preactivation.

A preactivation source remaining active MUST NOT:

- establish occupancy
- maintain occupancy
- indefinitely extend provisional lighting
- prevent vacancy

This is especially important for door contacts.

A door may remain open for minutes without implying that the controlled lighting area remains occupied.

Repeated new active transitions may restart or refresh preactivation where appropriate.

---

# 10. Scope of Preactivation

Preactivation specifically addresses immediate local occupancy flow.

A useful test is:

> Does this event provide strong evidence that someone may enter this lighting area within approximately the next few seconds?

In scope:

- local PIR immediately outside the area
- transition PIR between adjacent spaces
- door opening directly into or adjacent to the area
- curtain-style or narrowly constrained boundary motion sensors

Out of scope:

- geographic arrival
- Home Assistant `person` entering a geographic Zone
- phone connecting to home Wi-Fi
- vehicle arrival
- calendar events
- schedules
- general home/away state
- other long-horizon prediction

These signals may be excellent Home Assistant automation triggers, but they have different timing and lifecycle semantics.

For example:

    phone joins home Wi-Fi after sunset
        -> outdoor lights ON
        -> remain on until another unrelated event

is a useful Home Assistant automation, but it is not Zone-Aware Lighting preactivation.

Preactivation follows:

    local transition evidence
        -> probable occupancy within seconds
        -> provisional lighting
        -> occupancy confirmation OR withdrawal

---

# 11. Shared Boundary Sensors

The same physical preactivation sensor may participate in multiple area controllers.

Example:

    Master Bedroom
          |
      Boundary PIR
          |
      Living Room

The Boundary PIR may be configured as a preactivation sensor for both.

If:

    Master occupied
    Living vacant
    Boundary PIR activates

then:

    Master controller:
        already occupied
        -> no provisional action required

    Living controller:
        vacant
        -> provisionally illuminate Living

The blueprint does not need to infer travel direction.

---

## Both Adjacent Areas Vacant

If both sides of a shared boundary are vacant, both may provisionally illuminate.

This is acceptable.

The preferred failure mode is:

> a small amount of unnecessary LED lighting for several seconds

rather than unreliable direction inference.

Each area independently withdraws provisional lighting unless its Occupancy Sensors confirm occupancy.

---

# 12. Sensor Placement Guidance

Preactivation works best when its sensor represents a specific transition rather than broad adjacent-room activity.

Useful implementations may include:

- narrow-field PIR
- curtain PIR
- physically masked PIR
- PIR whose view is constrained by mounting geometry
- downward-facing PIR
- door contact

A small detection region near a physical boundary may provide more useful preactivation evidence than a broad whole-room detector.

For example, a PIR intentionally constrained to approximately a small doorway or several-square-foot floor region can provide highly specific transition evidence.

This is deployment guidance, not a blueprint requirement.

---

# 13. Logical Occupancy States

The implementation does not necessarily need to expose or persist entities matching these exact state names, but its behavior MUST correspond to them.

---

## VACANT

No confirmed occupancy currently exists.

Transitions:

    Occupancy Sensor ON
        -> CONFIRMED OCCUPANCY

    Preactivation Sensor active transition
        -> PROVISIONAL ACTIVATION

    Additional Retention Sensor ON
        -> remain VACANT

---

## PROVISIONAL ACTIVATION

A preactivation event has justified temporary lighting but has not established occupancy.

Behavior:

    activate selected target provisionally
    start preactivation timeout

Transitions:

    Occupancy Sensor ON
        -> CONFIRMED OCCUPANCY

    timeout with no Occupancy Sensor ON
        -> VACANT
        -> withdraw provisional lighting

Additional Retention Sensors cannot confirm this state.

---

## CONFIRMED OCCUPANCY

At least one Occupancy Sensor has provided trusted positive occupancy evidence.

Positive evidence includes:

    Occupancy Sensor ON
        OR
    Additional Retention Sensor ON

while an occupancy session already exists.

When all Occupancy and Additional Retention Sensors explicitly report `off`:

    -> POSSIBLY VACANT

---

## POSSIBLY VACANT

No positive occupancy evidence currently exists.

Begin `vacancy_timeout`.

During timeout:

    Occupancy Sensor ON
        -> CONFIRMED OCCUPANCY

    Additional Retention Sensor ON
        -> return to confirmed occupancy / cancel vacancy

If all relevant sensors remain explicitly `off` for the complete vacancy timeout:

    -> VACANT
    -> automatic lighting may be withdrawn

---

# 14. Vacancy Rules

Vacancy requires:

    ALL Occupancy Sensors == off
        AND
    ALL Additional Retention Sensors == off

for the complete configured vacancy timeout.

Before executing an automatic turn-off action, the blueprint MUST re-evaluate all relevant sensor states.

If any relevant sensor has returned to `on`:

    -> keep lighting on

Positive occupancy evidence always wins a race against vacancy timeout expiration.

Prevent shutdown when renewed occupancy is observable before dispatch;
otherwise promptly restore the affected lighting, as described in Section 31.

---

# 15. Unknown and Unavailable Sensor States

Sensor failure must bias toward maintaining useful lighting rather than incorrectly proving vacancy.

Interpret states as:

    on
        = positive occupancy evidence

    off
        = explicit clear evidence

    unknown
        = insufficient evidence of vacancy

    unavailable
        = insufficient evidence of vacancy

`unknown` and `unavailable` MUST NOT be interpreted as equivalent to `off`.

Confirmed vacancy therefore requires every applicable Occupancy and Additional Retention Sensor to explicitly report `off`.

---

# 16. Activation Is Separate From Occupancy

Occupancy evidence determines whether automatic activation is justified.

It does not necessarily mean lighting should actually turn on.

Before transitioning a controlled target from OFF to ON, the blueprint evaluates an Activation Gate.

Conceptually:

    occupancy/preactivation request
                |
                v
        ACTIVATION GATE
          /         \
      permit       inhibit
        |             |
        v             v
     activate       no action

The Activation Gate is evaluated only for automatic OFF -> ON behavior.

Restoring lighting just extinguished by an in-flight shutdown race is
compensation within the existing session, not a new activation request. It
preserves the selected target and does not reevaluate the Activation Gate.

---

# 17. Activation Permission

Activation permission consists of:

1. built-in illuminance evaluation
2. optional additional Home Assistant conditions

All common activation requirements apply before target selection.

Target-specific selection conditions are additive and cannot bypass global activation permission.

---

# 18. Illuminance

Illuminance is a first-class activation permission mechanism because ambient light is intrinsic to automatic lighting behavior.

Illuminance does NOT represent occupancy.

Illuminance MUST NOT:

- establish occupancy
- retain occupancy
- confirm preactivation
- establish vacancy
- automatically turn off lighting already on

It is evaluated only when automatic activation is requested.

---

# 19. Multiple Illuminance Sensors

The blueprint SHOULD support zero or more Home Assistant illuminance sensors.

Example:

    illuminance_sensors:
      - sensor.living_room_lux
      - sensor.window_side_lux
      - sensor.transition_lux

When multiple sensors are configured, the blueprint calculates an effective illuminance value.

Supported aggregation methods SHOULD include:

- `minimum`
- `maximum`
- `average`
- `median`

When only one sensor is configured, all aggregation methods naturally produce the same effective value.

---

## Aggregation Semantics

Example readings:

    Sensor A: 35 lux
    Sensor B: 55 lux
    Sensor C: 280 lux

Results:

    minimum = 35 lux
    maximum = 280 lux
    average ≈ 123 lux
    median = 55 lux

Interpretations:

### Minimum

Allows activation when any measured portion of the area remains dark.

### Maximum

Inhibits activation when any measured portion is sufficiently bright.

### Average

Represents general measured illumination across the selected sensors.

### Median

Reduces the influence of an unusually bright or dark outlier and may be useful with three or more sensors.

Default aggregation SHOULD initially be `average` unless implementation/testing demonstrates a better default.

---

# 20. Illuminance Threshold

When illuminance sensing is configured:

    effective illuminance >= threshold
        -> inhibit automatic activation

    effective illuminance < threshold
        -> illuminance permits activation

The precise comparison semantics should remain stable once released.

---

# 21. Invalid Illuminance Readings

Only valid numeric illuminance readings participate in aggregation.

If:

    Sensor A = 40
    Sensor B = unavailable
    Sensor C = 60

then:

    aggregate Sensor A + Sensor C only

If no configured illuminance sensor contains a valid numeric value:

    default behavior = allow activation

Lighting availability should fail safe toward usable illumination rather than darkness due to a sensor or network failure.

A future configurable failure policy may be considered if real-world demand exists, but it is not required for the initial version.

---

# 22. Illuminance Does Not Cause Deactivation

Illuminance is evaluated only for OFF -> ON automatic activation.

Example:

    room dark
    occupancy detected
        -> lights ON

    sunlight later increases
    illuminance rises above threshold

Zone-Aware Lighting does NOT automatically turn the lights off solely because the illuminance threshold has been crossed.

Automatic daylight harvesting and continuous daylight-responsive lighting are outside the initial project scope.

This also avoids feedback issues where the controlled lights themselves alter the measured illuminance.

---

# 23. Additional Activation Conditions

The blueprint SHOULD expose an optional native Home Assistant Condition selector.

Purpose:

> Additional conditions that must be true before automatic lighting activation is permitted.

These conditions apply globally to automatic activation.

Examples include:

- Sleep Mode must be off
- Party Mode must be off
- house mode must not be Away
- particular time ranges
- sun conditions
- another entity state
- any other condition supported by the Home Assistant condition UI

The blueprint SHOULD rely on Home Assistant's native condition system rather than implement custom condition types.

---

## Condition Semantics

Home Assistant's normal positive condition semantics should be preserved.

For example:

    Sleep Mode == off

means activation is permitted only when Sleep Mode is off.

Avoid designing a custom "inhibitor" language requiring users to mentally invert conditions.

---

# 24. Common Activation Gate

Both direct occupancy activation and preactivation use the same common Activation Gate.

Conceptually:

    Occupancy request ----------+
                               |
    Preactivation request ------+
                               |
                               v
                     Illuminance permits?
                               |
                               v
                    Activation conditions pass?
                               |
                       +-------+-------+
                       |               |
                      yes              no
                       |               |
                       v               v
                select target        no action

A preactivation event inhibited by the Activation Gate MUST NOT prevent a subsequent Occupancy Sensor event from being evaluated independently.

Each new automatic activation request may reevaluate current activation conditions.

---

# 25. Lighting Targets

The blueprint must support a normal/default lighting target.

The project intentionally focuses on determining:

> When should this lighting area be illuminated?

It should avoid expanding into continuous brightness or color-temperature management.

Those behaviors compose naturally with other Home Assistant systems such as Adaptive Lighting.

---

# 26. Relationship to Adaptive Lighting

Zone-Aware Lighting and Adaptive Lighting solve complementary problems.

Conceptually:

    Zone-Aware Lighting
        -> SHOULD this area be illuminated?

    Adaptive Lighting
        -> HOW should these illuminated lights look?

Zone-Aware Lighting owns:

- occupancy-driven activation
- occupancy lifecycle
- local transition/preactivation
- vacancy determination
- activation permission
- target selection

Adaptive Lighting may independently own:

- brightness
- color temperature
- circadian adaptation
- light appearance
- related manual-control behavior

Zone-Aware Lighting should remain composable with Adaptive Lighting rather than reproduce those capabilities.

---

# 27. Optional Alternate Lighting Target

Some controlled areas use different physical light sources under different conditions.

Example:

Day:

    bright overhead lighting

Night:

    under-bed lighting
    cabinet-base lighting
    low-level navigation lighting

The occupancy model should not need to be duplicated merely because the desired lighting target changes.

The initial implementation SHOULD therefore support:

- one default target
- one optional alternate target
- one optional native Home Assistant condition block selecting the alternate target

Do NOT implement an arbitrary multi-profile engine in the initial version.

---

# 28. Alternate Target Selection

Target selection occurs only after the common Activation Gate has passed.

Conceptually:

    AUTOMATIC ACTIVATION REQUEST
              |
              v
       Illuminance permits?
              |
              v
    Global activation conditions pass?
              |
              v
    Alternate-target conditions pass?
            /     \
          yes      no
           |        |
           v        v
      Alternate   Default
        Target     Target

Global Activation Conditions MUST NOT need to be duplicated in Alternate Target Conditions.

Alternate Target Conditions are additive.

They answer:

> Given that activation is already permitted, which target should represent this lighting area?

They do NOT answer:

> Is automatic lighting permitted?

---

## Example

Global Activation Conditions:

    Sleep Mode == off
    House Mode != Away

Alternate Target Conditions:

    Time after 10:30 PM

At 11:00 PM:

If:

    Sleep Mode == on

then:

    no automatic activation

If:

    Sleep Mode == off
    House Mode != Away

then activation is globally permitted.

Because:

    time > 10:30 PM

the alternate navigation-light target is selected.

The global conditions do not need to be repeated inside Alternate Target Conditions.

---

# 29. Alternate Target Changes During Occupancy

For the initial version, target selection SHOULD occur when automatic activation begins and remain fixed for that occupancy session.

Example:

    10:58 PM
    occupancy detected

    Alternate condition is false
        -> default overhead target ON

    11:00 PM
    alternate condition becomes true

Initial-version behavior:

    leave current target unchanged

    room eventually becomes vacant
        -> default target OFF

    next occupancy
        -> evaluate conditions again
        -> alternate target ON

This behavior is deliberately conservative and predictable.

---

## Future Graceful Transition

A future version MAY support active target transitions while a room remains occupied.

Possible future behavior:

    current target = overhead
    alternate condition becomes true
        -> navigation lights ON
        -> short transition
        -> overhead lights OFF
        -> occupancy session continues uninterrupted

This is potentially useful but is intentionally deferred until real-world experience demonstrates that the additional complexity is worthwhile.

---

# 30. Manual Lighting and Automation Ownership

The blueprint MUST NOT assume:

    target ON
        == confirmed occupancy

A light may already be ON because:

- someone manually turned it on
- another automation turned it on
- preactivation turned it on provisionally
- another system controls the same fixture

A failed preactivation MUST NOT blindly turn off a target that was already ON before the provisional action.

Example:

    bathroom light manually ON
    vestibule preactivation occurs
    no bathroom occupancy occurs
    preactivation timeout expires

Expected:

    bathroom light remains ON

The implementation must track enough state to know whether provisional activation actually introduced lighting that should be withdrawn.

Do not infer ownership solely from target state.

Manual lighting actions do not disable or end an occupancy session. The initial
version does not attempt to detect manual takeover. A light provisionally
introduced by this automation remains eligible for withdrawal if someone
switches it off and then on again before the confirmation timeout.

---

# 31. Concurrency and Race Conditions

The implementation MUST explicitly account for event races.

---

## Preactivation Timeout vs Occupancy Detection

Immediately before withdrawing provisional lighting:

    recheck ALL Occupancy Sensors

If any is ON:

    confirmed occupancy wins

Prevent shutdown when renewed occupancy is observable before dispatch;
otherwise promptly restore the affected lighting. An OFF command already in
flight may cause a brief interruption that the blueprint cannot prevent.

---

## Vacancy Timeout vs Redetection

Immediately before automatic shutoff:

    recheck ALL Occupancy Sensors
    recheck ALL Additional Retention Sensors

If any is ON:

    cancel shutdown
    retain lighting

If occupancy or retention evidence invalidates vacancy while the OFF command
is in flight, promptly restore only the lights included in that shutdown.
`unknown` and `unavailable` also invalidate confirmed vacancy. Retention
evidence still cannot confirm provisional activation.

Restoration preserves the current session and selected target. It does not
reevaluate illuminance, Activation Conditions, or Alternate Target Conditions,
and must not turn on other lights that were already off before shutdown.

---

## Repeated Preactivation

Repeated preactivation events may restart or extend the confirmation period as appropriate.

They MUST NOT downgrade or interfere with confirmed occupancy.

---

## Simultaneous Adjacent Occupancy

Two independent areas may become occupied simultaneously.

One area's confirmation MUST NOT be interpreted as evidence that another area is vacant.

---

# 32. Automation Execution Model

Avoid relying on one fragile, long-running automation execution to represent the entire lifetime of an occupancy session if trigger restarts can destroy important context.

The implementation should prefer:

- event-driven branches
- explicit state checks
- trigger IDs
- idempotent actions
- timers where appropriate
- minimal persistent helper state only where required

The exact mechanism is an implementation decision.

The behavior defined in this specification is authoritative.

The initial implementation uses one run per session and ignores outer triggers
while that run is active. The provisional confirmation wait starts after
`light.turn_on` completes. Occupancy still ON at that point confirms normally,
but an entire ON/OFF pulse during the blocking service call may be missed.
This accepted limitation is most relevant to short-pulse sensors or slow light
service handlers; it does not require adding event-latching helpers.

---

# 33. Persistent State

Persistent helpers should be introduced only when required for correctness.

Possible reasons include:

- distinguishing provisional activation ownership
- surviving Home Assistant restart during a timer
- preventing accidental shutdown of manually activated lighting

Avoid creating helper requirements merely because a state-machine representation is convenient.

The simplest valid automation instance should remain simple to configure.

---

# 34. Home Assistant Restart Behavior

Restart behavior must be safe.

After restart:

- `unknown` or `unavailable` sensors must not establish vacancy
- manually active targets must not be blindly shut down
- stale provisional state should not create unexpected automatic shutdown
- losing an active run intentionally fails ON rather than reconstructing
  ownership from current light or sensor states

If persistent timers or helpers are used, restart semantics must be explicitly documented and tested.

The initial implementation uses no persistent session helpers. Restarting Home
Assistant or reloading an automation in a way that replaces its active run
abandons its session without switching lights off. Existing lighting can remain
ON indefinitely; automatic management resumes on a subsequent qualifying
activation event. No immediate startup reconciliation is required.

---

# 35. Progressive Configuration Model

The UI should present complexity progressively.

A user wanting conventional motion lighting should not need to understand advanced features.

Suggested organization:

## Basic: Occupancy

- Occupancy Sensors
- Vacancy Timeout

## Basic: Lighting

- Default Target

## Optional: Ambient Light

- Illuminance Sensors
- Aggregation Mode
- Illuminance Threshold

## Advanced: Extended Detection

- Preactivation Sensors
- Preactivation Confirmation Timeout
- Additional Retention Sensors

## Advanced: Activation Conditions

- Native Home Assistant Activation Conditions

## Advanced: Alternate Lighting

- Alternate Target
- Alternate Target Conditions

Advanced sections should default to values that preserve basic conventional behavior.

---

# 36. Progressive Enhancement Examples

## Level 1: Traditional Motion Lighting

    occupancy_sensors:
      - binary_sensor.room_motion

Behavior:

    motion
        -> ON

    clear for vacancy timeout
        -> OFF

---

## Level 2: PIR + mmWave

    occupancy_sensors:
      - binary_sensor.room_motion
      - binary_sensor.room_occupancy

Behavior:

    either ON
        -> occupied

    both OFF for timeout
        -> vacant

---

## Level 3: Selective mmWave Authority

    occupancy_sensors:
      - binary_sensor.room_motion

    additional_retention_sensors:
      - binary_sensor.room_mmwave_occupancy

Behavior:

    PIR
        -> may turn ON

    mmWave
        -> may prevent OFF
        -> may not independently turn ON

---

## Level 4: Extended Detection

    preactivation_sensors:
      - binary_sensor.boundary_motion

    occupancy_sensors:
      - binary_sensor.room_motion

Behavior:

    boundary motion
        -> provisional ON

    room motion
        -> confirmed occupancy

---

## Level 5: Lighting Permission

    occupancy_sensors:
      - binary_sensor.room_motion

    illuminance_sensors:
      - sensor.room_lux
      - sensor.window_lux

    illuminance_aggregation:
      median

    illuminance_threshold:
      100

Behavior:

    occupancy
        -> evaluate effective lux
        -> activate only if illumination permits

---

## Level 6: Additional Conditions

    activation_conditions:
      - Sleep Mode is OFF

Behavior:

    occupancy
        -> illuminance permits
        -> Sleep Mode condition passes
        -> activate

---

## Level 7: Alternate Night Lighting

Default target:

    overhead lighting

Alternate target:

    under-bed / cabinet / navigation lighting

Alternate condition:

    nighttime condition

Behavior:

    activation permitted
        -> select appropriate target
        -> target remains selected for occupancy session

---

# 37. Example: Vestibule / Bathroom / Laundry

## Vestibule

    occupancy_sensors:
      - binary_sensor.vestibule_motion

    vacancy_timeout:
      30 seconds

The vestibule controls only its own lighting.

---

## Bathroom

    preactivation_sensors:
      - binary_sensor.vestibule_motion

    occupancy_sensors:
      - binary_sensor.bathroom_motion

    preactivation_timeout:
      10 seconds

    vacancy_timeout:
      180 seconds

Sequence:

    vestibule motion
        -> bathroom provisionally ON

    bathroom motion within 10 seconds
        -> confirmed occupancy

    no bathroom motion
        -> provisional bathroom lighting withdrawn

---

## Bathroom With mmWave Retention

    preactivation_sensors:
      - binary_sensor.vestibule_motion

    occupancy_sensors:
      - binary_sensor.bathroom_motion

    additional_retention_sensors:
      - binary_sensor.bathroom_mmwave

The mmWave entity may preserve occupancy after PIR clears.

The mmWave entity cannot confirm vestibule-triggered preactivation.

---

## Laundry / Office

    preactivation_sensors:
      - binary_sensor.vestibule_motion

    occupancy_sensors:
      - binary_sensor.laundry_occupancy

    preactivation_timeout:
      10 seconds

    vacancy_timeout:
      180+ seconds

The vestibule expands the effective detection aperture so lighting may be available before someone has entered deeply enough for the laundry's room sensor to acquire occupancy.

---

# 38. Example: Front Door / Entry Lighting

    preactivation_sensors:
      - binary_sensor.front_door

    occupancy_sensors:
      - binary_sensor.entry_motion

Sequence:

    front door CLOSED -> OPEN
        -> provisionally illuminate entry

If:

    entry motion detected
        -> confirmed occupancy

If:

    no entry occupancy detected
        -> withdraw provisional lighting after timeout

The front door remaining open must not retain occupancy.

---

# 39. Example: Shared Master / Living Boundary

Boundary sensor:

    binary_sensor.master_living_boundary_motion

Configure the same entity as a preactivation source for both automation instances.

Master controller:

    preactivation_sensors:
      - binary_sensor.master_living_boundary_motion

Living controller:

    preactivation_sensors:
      - binary_sensor.master_living_boundary_motion

If Master is occupied and Living is vacant:

    boundary motion
        -> Living provisionally activates

If Living is occupied and Master is vacant:

    boundary motion
        -> Master provisionally activates

No direction inference is required.

---

# 40. Example: Bedroom With Bed Occupancy

Assume the bed integration already provides:

    binary_sensor.bed_occupied
    device_class: occupancy

Possible configuration:

    occupancy_sensors:
      - binary_sensor.bedroom_motion

    additional_retention_sensors:
      - binary_sensor.bedroom_mmwave
      - binary_sensor.bed_occupied

The bed entity cannot automatically light the room if configured as additional retention.

But once occupancy has been established:

    bed occupied
        -> prevents false vacancy

This is useful for sleeping or other extremely stationary occupancy.

If only raw pressure is available, the user should first create an appropriate Home Assistant Occupancy binary sensor.

---

# 41. Example: Day and Night Lighting

Default target:

    bright overhead lights

Alternate target:

    under-furniture / cabinet-base navigation lights

Alternate Target Conditions:

    nighttime schedule or other user-defined HA condition

During daytime occupancy:

    activation allowed
        -> default target

During nighttime occupancy:

    activation allowed
        -> alternate target

The same occupancy, preactivation, retention, vacancy, illuminance, and global activation model is shared.

Separate day/night occupancy automations are unnecessary.

---

# 42. Suggested Timing Defaults

## Preactivation Timeout

Suggested default:

    10 seconds

Expected practical range:

    approximately 5-15 seconds

Question answered:

> Did someone actually enter the predicted destination?

---

## Vacancy Timeout

Suggested default:

    180 seconds

Typical starting ranges:

    transitional spaces:
        20-60 seconds

    bathroom:
        120-180 seconds

    kitchen:
        120-300 seconds

    living / television:
        180-300 seconds

    office:
        180-300+ seconds

    bedroom:
        potentially longer or subject to additional sleep-mode policy

Question answered:

> Has occupancy evidence been absent long enough that we are comfortable declaring this area vacant?

These are starting points, not hard requirements.

---

# 43. Acceptance Tests

## Test 1: Traditional Motion Lighting

Given:

    one Occupancy Sensor
    no optional features

When:

    Occupancy Sensor ON

Then:

    target ON

When:

    Occupancy Sensor OFF
    and remains OFF for vacancy_timeout

Then:

    target OFF

---

## Test 2: Multiple Occupancy Sensors

Given:

    PIR
    mmWave

When:

    PIR ON
        -> target ON

Then:

    PIR OFF
    mmWave ON
        -> target remains ON

When:

    PIR OFF
    mmWave OFF
        -> vacancy timeout begins

If both remain OFF:

    target OFF

---

## Test 3: Brief mmWave False Negative

Given confirmed occupancy:

    PIR OFF
    mmWave OFF
        -> vacancy timer begins

Then:

    mmWave ON before timeout

Expected:

    vacancy canceled
    target remains ON

---

## Test 4: Retention Cannot Activate

Given:

    area vacant
    target OFF

When:

    Additional Retention Sensor ON

Expected:

    target remains OFF
    no confirmed occupancy is established

---

## Test 5: Successful Preactivation

When:

    boundary PIR ON
        -> provisional target ON

Then:

    Occupancy Sensor ON before timeout

Expected:

    confirmed occupancy
    target remains ON

---

## Test 6: Failed Preactivation

When:

    boundary PIR ON
        -> provisional target ON

And:

    no Occupancy Sensor confirms

Expected:

    target returns to previous/off state after timeout

---

## Test 7: Retention Cannot Confirm Preactivation

When:

    preactivation occurs

Then:

    retention-only mmWave ON
    occupancy PIR remains OFF

Expected:

    preactivation remains unconfirmed
    provisional lighting is withdrawn when timeout expires

---

## Test 8: Door Preactivation

When:

    door CLOSED -> OPEN

Expected:

    adjacent lighting may provisionally activate

If door remains OPEN:

    door state does not retain occupancy

If occupancy does not confirm:

    provisional lighting is withdrawn

---

## Test 9: Two People Enter Adjacent Rooms

When:

    shared vestibule preactivation occurs

Then:

    Bathroom Occupancy ON
    Laundry Occupancy ON

Expected:

    both rooms independently reach confirmed occupancy

Neither room controller affects the other's lighting.

---

## Test 10: Shared Boundary With One Side Occupied

Given:

    Master occupied
    Living vacant

When:

    shared boundary PIR activates

Expected:

    Master remains normally occupied
    Living provisionally activates

---

## Test 11: Shared Boundary With Both Sides Vacant

Given:

    Master vacant
    Living vacant

When:

    shared boundary PIR activates

Expected:

    both may provisionally activate

If only Living subsequently confirms occupancy:

    Living remains ON
    Master withdraws provisional lighting

---

## Test 12: Illuminance Allows Activation

Given:

    effective lux < threshold

When:

    valid Occupancy activation occurs

Expected:

    activation permitted

---

## Test 13: Illuminance Inhibits Activation

Given:

    effective lux >= threshold

When:

    Occupancy activation occurs

Expected:

    occupancy may still be logically established
    target remains OFF

Illuminance affects automatic lighting activation, not occupancy evidence.

---

## Test 14: Partial Illuminance Failure

Given:

    Sensor A = 40 lux
    Sensor B = unavailable
    Sensor C = 60 lux

Expected:

    aggregate Sensor A and Sensor C only

---

## Test 15: Complete Illuminance Failure

Given:

    all configured illuminance sensors invalid/unavailable

When:

    otherwise valid activation occurs

Expected:

    activation allowed by default

---

## Test 16: Rising Illuminance Does Not Deactivate

Given:

    target automatically ON
    confirmed occupancy

When:

    lux rises above activation threshold

Expected:

    no illuminance-driven turn-off occurs

---

## Test 17: Additional Activation Condition

Given:

    Sleep Mode must equal OFF

When:

    Sleep Mode ON
    occupancy detected

Expected:

    occupancy may be logically established
    automatic lighting remains OFF

When:

    a later valid activation request occurs with Sleep Mode OFF

Expected:

    activation may proceed

---

## Test 18: Alternate Target

Given:

    common Activation Gate passes
    Alternate Target Conditions true

Expected:

    alternate target selected

If Alternate Target Conditions false:

    default target selected

---

## Test 19: Global Conditions Compound With Alternate Selection

Given:

    Global conditions:
        Sleep Mode OFF

    Alternate conditions:
        after 10:30 PM

At 11:00 PM with Sleep Mode ON:

    no target activates

At 11:00 PM with Sleep Mode OFF:

    activation permitted
    alternate target selected

Sleep Mode condition does not need to be duplicated in Alternate Target Conditions.

---

## Test 20: Alternate Condition Changes During Occupancy

Given:

    default target activated at 10:58 PM

When:

    alternate condition becomes true at 11:00 PM

Expected initial-version behavior:

    current default target remains active

After vacancy:

    current target turns off

At next activation:

    alternate target selected

---

## Test 21: Manual Lighting Survives Failed Preactivation

Given:

    target manually ON
    area vacant

When:

    preactivation occurs
    no occupancy confirmation occurs
    preactivation timeout expires

Expected:

    manually existing lighting remains ON

The automation must not withdraw lighting it did not provisionally introduce.

---

## Test 22: Sensor Unavailable During Vacancy

Given confirmed occupancy:

    PIR OFF
    mmWave unavailable

Expected:

    do not declare confirmed vacancy solely from these states

`unavailable` is not equivalent to `off`.

---

## Test 23: Occupancy Wins Timeout Race

When:

    vacancy or preactivation timeout expires

At approximately the same time:

    Occupancy Sensor becomes ON

Expected:

    sensor states are rechecked
    positive occupancy wins
    prevent shutdown when renewed occupancy is observable before dispatch;
    otherwise promptly restore the affected lighting

For an in-flight shutdown:

    restore only the affected lights
    preserve the current session and selected target
    restore even if activation permission or alternate selection has changed
    begin a fresh vacancy timeout after all occupancy and retention evidence clears

Additional Retention Sensors may cancel or reverse a confirmed-vacancy
shutdown, but must not confirm or reverse failed provisional activation alone.

---

## Test 24: Home Assistant Restart

Test restart while:

- vacant
- provisionally activated
- confirmed occupied
- vacancy timer running
- sensor unavailable
- target manually ON

Expected:

    no unsafe assumption of vacancy
    no blind shutdown of manually active lighting
    active runs may be abandoned, leaving existing lighting ON indefinitely
    automatic management resumes on a subsequent qualifying activation event

No persistent session reconstruction or startup reconciliation is required.

---

# 44. Initial Scope Boundaries

The initial version SHOULD support:

- one or more Motion/Occupancy sensors
- optional Motion/Occupancy retention sensors
- optional local Motion/Door/Opening preactivation sources
- configurable preactivation timeout
- configurable vacancy timeout
- multiple illuminance sensors
- min/max/average/median illuminance aggregation
- global activation conditions using the native Home Assistant condition editor
- one default target
- one optional alternate target
- native Home Assistant conditions for alternate-target selection
- safe handling of manual target state
- safe handling of unknown/unavailable sensors
- protection from activation/vacancy races

---

# 45. Explicitly Out of Scope for Initial Release

The initial release should NOT attempt to provide:

- arbitrary numeric occupancy sensor interpretation
- arbitrary binary sensor classes for occupancy
- arbitrary sensor state mappings
- arbitrary templates as occupancy inputs
- person tracking between areas
- directional travel inference
- Bayesian occupancy confidence scoring
- historical occupancy learning
- geographic/geofence preactivation
- Wi-Fi arrival preactivation
- vehicle arrival logic
- calendar-based occupancy prediction
- continuous daylight harvesting
- brightness management
- color-temperature management
- circadian lighting
- arbitrary numbers of lighting profiles
- dynamic profile priority systems
- active alternate-target transition during an occupancy session
- whole-house occupancy orchestration
- centralized coordination between room automation instances

Home Assistant itself or other specialized projects should remain responsible for these concerns.

---

# 46. Blueprint vs Integration Boundary

Zone-Aware Lighting should remain a blueprint as long as each controlled lighting area can be understood as:

    Home Assistant events/entities
        -> evaluate current state
        -> make discrete decision
        -> control this area's target

A future custom integration may become appropriate if the project eventually requires:

- its own persistent entity model
- centralized coordination across multiple areas
- continuous occupancy-confidence calculations
- historical learning
- dynamic sensor discovery
- service-call interception
- continuous scheduling
- exposed services
- shared occupancy state between independent lighting areas

Complexity alone does not require an integration.

The architectural dividing line is whether Zone-Aware Lighting remains an event-driven automation or becomes a persistent automation engine.

The initial design intentionally remains on the blueprint side of this boundary.

---

# 47. Architectural Invariants

These rules define the core behavior of the project.

1. Each automation instance owns one logical lighting area.

2. Occupancy Sensors are the only required sensor input.

3. Occupancy Sensors support one or more Home Assistant Motion and/or Occupancy binary sensors.

4. Any Occupancy Sensor may establish confirmed occupancy.

5. Every Occupancy Sensor inherently participates in retention.

6. Additional Retention Sensors are optional.

7. Additional Retention Sensors may prevent vacancy only after occupancy has been established.

8. Additional Retention Sensors may not independently activate lighting.

9. Additional Retention Sensors may not confirm preactivation.

10. Preactivation Sources are optional.

11. Preactivation represents local short-horizon transition evidence, not general prediction.

12. Preactivation may provisionally activate lighting.

13. Only an Occupancy Sensor may convert provisional activation into confirmed occupancy.

14. Preactivation sources are edge-triggered. Their continuing active state does not represent occupancy.

15. Vacancy requires all Occupancy and Additional Retention Sensors to be explicitly clear.

16. Vacancy must remain true for the complete configured vacancy timeout.

17. Sensor states must be rechecked immediately before automatic shutdown.

18. `unknown` and `unavailable` must not be treated as evidence of vacancy.

19. Illuminance affects OFF -> ON automatic activation only.

20. Illuminance does not establish or terminate occupancy.

21. Existing lighting must not be turned off merely because illuminance later exceeds the activation threshold.

22. Additional Activation Conditions apply globally to every automatic activation path. Compensating restoration after a racing shutdown preserves existing illumination and is not a new activation request.

23. Alternate Target Conditions are evaluated only after the common Activation Gate succeeds.

24. Alternate Target Conditions are additive and may never bypass global Activation Conditions.

25. The user must not need to duplicate global Activation Conditions within Alternate Target Conditions.

26. Target selection does not establish occupancy.

27. In the initial version, target selection remains fixed for the occupancy session.

28. A failed provisional activation must not turn off lighting that was already active before the provisional event.

29. One physical sensor may independently participate in multiple Zone-Aware Lighting automation instances.

30. One area's automation must never directly manipulate another area's lighting target.

31. Conventional single-motion-sensor lighting must remain a first-class and simple configuration.

32. Advanced features must remain optional and additive.

33. Device-specific sensor interpretation belongs outside the blueprint.

34. Zone-Aware Lighting determines when an area should be illuminated, not the continuous brightness or color characteristics of that illumination.

---

# 48. Guiding Principle

Zone-Aware Lighting should make conventional automatic lighting more robust and context-aware without requiring every installation to become sophisticated.

The simplest configuration remains:

    motion
        -> light

The architecture then allows users to selectively expand the aperture:

    motion
        +
    occupancy
        +
    retention evidence
        +
    immediate boundary transitions
        +
    ambient-light permission
        +
    Home Assistant conditions
        +
    contextual target selection

The system should prefer:

    fast positive occupancy detection
        +
    conservative vacancy determination
        +
    optional local preactivation
        +
    clean composition with the rest of Home Assistant

over attempting to make any one PIR, mmWave sensor, or other technology an authoritative representation of human occupancy.