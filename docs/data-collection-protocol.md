# Real sensor data collection protocol

This protocol collects labelled, stationary and controlled-motion ESP32 + MPU6050
telemetry for validating the SUBSENSE feature and evaluation pipeline. It is a
research procedure, not a mine-safety certification procedure. Do not perform
tests in an operating mine or expose people/equipment to unsafe conditions.

## Equipment and setup

- ESP32-S3-WROOM-1 development board and MPU6050 module, mounted as a single
  sensor node on a rigid fixture.
- A level stationary surface, a stable tilt rig with a measured support span,
  non-compressible shims of measured height, and a way to secure the rig.
- A computer that records serial JSON lines with UTC timestamps.
- For the multi-node test, at least two independently identified nodes and a
  shared time reference.

Record the following before each collection:

- sensor and board model/revision, including MPU6050 breakout identification;
- mounting method, orientation, fasteners/adhesive, and cable routing;
- configured and observed sampling rate, plus timestamp source and units;
- ambient temperature (and sensor temperature if available);
- firmware version or source revision and telemetry schema version;
- node ID, date/time, location description, rig dimensions and calibration;
- any interruptions, resets, dropped records, or changes to the setup.

## Collection sequence

1. **Stationary noise and drift:** secure the node on the fixture with no
   intentional motion. Record continuously for 24–48 hours. Do not move or
   remount it during the run. Note environmental changes and interruptions.
   Use this run as the stationary input to `ai_engine.evaluation.noise_floor`.
2. **Known-angle tilt steps:** on the secured rig, apply measured shims at one
   support to create a sequence of static angles. At every step, log the
   unmodified serial stream, record the stable hold start/end times, then
   return to the baseline. Repeat for each axis/orientation that the rig
   supports. Keep the fixture restrained and within the sensor's rated range.
3. **Known-angle ramps:** raise the supported end slowly and continuously,
   holding the start/end times and maximum shim height. Include a return ramp
   to baseline. Record the ramp rate and do not infer the true angle from the
   sensor output; compute it from the rig geometry.
4. **Vibration taps:** with the node firmly fixed, apply repeatable, gentle
   taps to the fixture at recorded times. Keep tap location and method
   consistent, separate taps sufficiently to label individual events, and
   include quiet intervals before and after. Do not strike the sensor board.
5. **Multi-node test:** mount all nodes on the same rigid test structure at
   documented positions. Synchronize their clocks, record a common stationary
   period, then apply the same controlled tilt step/ramp or vibration input.
   Record which nodes were physically affected and the common event times.
6. **Label and inspect:** preserve the original serial file unchanged. Create
   a separate event label CSV using the format below. Check timestamp
   monotonicity, missing intervals, node IDs and labels before evaluation.

### Angle from shim height

Measure the support-to-support horizontal span `L` in the rig's neutral
position and the vertical shim height `h` under the raised support, in the same
units. For a rigid straight support, the applied angle is:

`angle_deg = atan(h / L) * 180 / pi`

Use the measured change in height relative to the baseline shim stack. Record
the actual `h` and `L` for each hold; do not substitute a nominal shim size.
This geometric angle describes the rig setting and not necessarily the angle
at the sensing element if the mount flexes or slips.

## Label file

Use UTF-8 CSV with this exact header:

```csv
event_id,node_id,start_time,end_time,event_type,true_angle_deg
```

`start_time` and `end_time` are inclusive UTC ISO-8601 timestamps with an
explicit timezone offset. `true_angle_deg` is the rig-derived angle for tilt
events; use an empty value for event types without a meaningful tilt angle.
Use one row per event and affected node. For a multi-node event, repeat the
event ID with each affected node ID. Suggested event types include
`tilt_step`, `tilt_ramp`, `vibration_tap`, and `multi_node_tilt`. Store quiet
control periods separately in the data notes; never label an unreviewed gap as
normal merely because no event row covers it.

`tools/log_serial_to_csv.py --label-file ...` uses these intervals to set
`label=1` for readings inside a matching event interval and `label=0` for
readings outside all intervals. Therefore, only use that option when the
label file covers the complete recording and all out-of-event periods have
been reviewed as non-event. Without `--label-file`, the output label is blank
and is not ready for supervised evaluation.

## Output and handling

The logger writes
`timestamp,node_id,tilt_x,tilt_y,accel_x,accel_y,accel_z,vibration,label`.
Keep raw serial logs, label files, and collection metadata together but do not
commit sensitive site information, credentials, or unreviewed personal data.
The noise-floor tool expects a stationary CSV with the timestamp, node, tilt,
and acceleration fields; it reports empirical sensor noise, drift and
false-alarm thresholds, not guaranteed field detection limits.
