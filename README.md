# Zone-Aware Lighting

Occupancy-driven lighting for one controlled lighting area, packaged as a Home
Assistant automation blueprint.

**Version: 0.1.0 (experimental).** Initial real-device validation is pending.
Start with one noncritical light and keep manual control available.

## Compatibility and Validation

| Item | Version / status |
|---|---|
| Blueprint | 0.1.0, experimental |
| Declared minimum Home Assistant | 2025.4.0; not validated on that minimum |
| Automated tests | Passed on Home Assistant 2026.10.4 with mocked sensors and light services |
| Planned live-device testing | Home Assistant 2026.11.1; not yet completed |

The Home Assistant version requirement is separate from the blueprint version.
Python 3.14 or newer is required only to run the test harness; blueprint users
do not need to install a separate Python environment.

## Installation

### Local installation

1. Copy [`zone_aware_lighting.yaml`](zone_aware_lighting.yaml) into
   `blueprints/automation/zone_aware_lighting/zone_aware_lighting.yaml` under your
   Home Assistant configuration directory. Create the directories if needed.
2. Open **Settings > Automations & scenes > Blueprints**.
3. Find **Zone-Aware Lighting** and create an automation from it.

### Import from GitHub

Once the blueprint has been pushed to GitHub, use **Import Blueprint** on the
Blueprints page with this URL:

```text
https://github.com/jd-hicks/zone-aware-lighting/blob/main/zone_aware_lighting.yaml
```

The `main` URL follows ongoing development, not a fixed release. Check the
displayed blueprint version when importing or updating.

## Basic Use

Select:

- One or more **Occupancy Sensors** with Motion or Occupancy device class.
- A **Default Target** containing only the lights for this area.
- A **Vacancy Timeout**.

Any Occupancy Sensor turning ON can activate lighting. Lights turn OFF only
after every Occupancy and Additional Retention Sensor has explicitly remained
OFF for the vacancy timeout. No optional features are needed.

For a first trial, use one sensor, one noncritical light, and a short timeout
such as 15 seconds. Temporarily disable other motion-light automations
controlling that light. Verify activation, shutdown, and redetection during the
countdown before adding optional features.

Optional features include:

- Additional Retention Sensors that prevent vacancy but cannot activate lights
  or confirm preactivation.
- Local, OFF-to-ON Preactivation Sensors that provisionally illuminate the area.
- Illuminance aggregation and native Home Assistant activation conditions.
- An alternate target selected when activation begins and retained for the session.

See the [design specification](docs/design.md) for sensor roles, behavior, and
acceptance criteria.

## Known Behavior and Limitations

- **Restart/reload fails ON.** If a restart or reload replaces the active run,
  the session is abandoned without switching lights off. Existing lighting can
  remain ON indefinitely; management resumes on a subsequent qualifying
  activation event.
- **Manual operation does not suspend automation or reset timers.** A manually
  switched-on light can turn OFF shortly afterward if an existing session
  reaches its shutdown deadline. Failed preactivation does not withdraw lights
  that were already ON before that provisional activation.
- **Shutdown races are handled conservatively.** Renewed occupancy observable
  before dispatch prevents shutdown. If shutdown is already in flight, affected
  lighting is promptly restored within the same session. A brief interruption
  may be unavoidable.
- **Short confirmation pulses can be missed during a blocking service call.**
  The provisional confirmation wait starts after `light.turn_on` completes.
  Occupancy still ON then confirms normally; an entire ON/OFF pulse during
  that service call may be missed.

## Versioning

The project uses `MAJOR.MINOR.PATCH` versions, displayed in the blueprint
description and recorded with matching Git tags such as `v0.1.0`.

- Before `1.0.0`, patch releases contain compatible fixes; minor releases may
  introduce features or breaking changes, which must be documented.
- `1.0.0` will indicate a stable configuration and behavioral contract.
- After `1.0.0`, compatible features increment the minor version and breaking
  changes increment the major version.

For each release:

1. Update the displayed version in the blueprint and this README.
2. Run the tests and record any live-device validation separately.
3. Commit the release contents, then create and push an annotated tag:

   ```sh
   git tag -a v0.1.0 -m "Zone-Aware Lighting v0.1.0 - experimental"
   git push origin v0.1.0
   ```

4. Publish a GitHub Release from the tag with changes, compatibility, known
   limitations, and any migration steps. Mark experimental releases as
   pre-releases.

Use the actual release version in the commands. Do not move published tags;
publish a new version for subsequent fixes. Not every commit needs a release tag.

## Automated Testing

The blueprint is tested by running it inside a real Home Assistant core, with
mocked sensors and light services. The tests in [`tests/`](tests/) cover the
Acceptance Tests in [`docs/design.md`](docs/design.md). The test suite is not
needed to use the blueprint and does not replace live-device testing.

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest
```

[`requirements-test.txt`](requirements-test.txt) currently pins a test harness
targeting Home Assistant 2026.10.4. The planned live test on 2026.11.1 does not
change that automated-test pin. To run automated tests against a newer release,
update the pin to the `pytest-homeassistant-custom-component` version that
targets it.
