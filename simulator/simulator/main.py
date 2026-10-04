"""
SUBSENSE Simulator — Main Entry Point

Usage
-----
    # Run from the subsense/ project root
    python -m simulator.main --scenario normal
    python -m simulator.main --scenario gradual_tilt --interval 0.5
    python -m simulator.main --scenario multi_node_event --duration 120
    python -m simulator.main --list

Arguments
---------
  --scenario    Name of the scenario to run (default: normal)
  --interval    Seconds between readings per node (default: 1.0)
  --duration    How many seconds to run; omit for infinite loop
  --list        Print all available scenarios and exit
  --dry-run     Generate readings but do NOT publish to MQTT (for testing)
"""

import argparse
import signal
import sys
import time

import structlog

# Bootstrap structlog before any other imports that might log
import logging
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
import structlog as sl
sl.configure(
    processors=[
        sl.stdlib.add_log_level,
        sl.processors.TimeStamper(fmt="%H:%M:%S"),
        sl.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=sl.make_filtering_bound_logger(logging.INFO),
    logger_factory=sl.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("simulator")

from simulator.config import sim_settings
from simulator.scenarios import SCENARIOS, ALL_NODES
from simulator.node import SensorNode, NodeBaseline
from simulator.publisher import SimulatorPublisher


# ── Argument parsing ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m simulator.main",
        description="SUBSENSE ESP32 sensor node simulator",
    )
    p.add_argument(
        "--scenario",
        default="normal",
        choices=list(SCENARIOS.keys()),
        help="Scenario to simulate (default: normal).",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=sim_settings.publish_interval,
        help="Seconds between readings per node (default: 1.0).",
    )
    p.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Total seconds to run. Omit for infinite loop.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="Print all available scenarios and exit.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate readings but skip MQTT publish (unit-test mode).",
    )
    return p


def list_scenarios() -> None:
    print("\n  Available SUBSENSE scenarios:\n")
    for name, cfg in SCENARIOS.items():
        print(f"  ✦ {name:22s}  {cfg.description[:72]}...")
    print()


# ── Node factory ─────────────────────────────────────────────────────────────

# Per-node baseline tilt values — in a real system these would come from
# a calibration database. For the simulator they are hardcoded.
NODE_BASELINES: dict[str, NodeBaseline] = {
    "N01": NodeBaseline(tilt_x=1.00, tilt_y=0.80),
    "N02": NodeBaseline(tilt_x=0.85, tilt_y=1.10),
    "N03": NodeBaseline(tilt_x=1.20, tilt_y=0.60),
    "N04": NodeBaseline(tilt_x=0.50, tilt_y=0.90),
    "N05": NodeBaseline(tilt_x=1.40, tilt_y=1.20),
    "N06": NodeBaseline(tilt_x=0.70, tilt_y=0.55),
}


def create_nodes(scenario_name: str) -> list[SensorNode]:
    cfg = SCENARIOS[scenario_name]
    nodes = []
    for node_id, zone_id in ALL_NODES.items():
        node = SensorNode(
            node_id=node_id,
            zone_id=zone_id,
            baseline=NODE_BASELINES.get(node_id, NodeBaseline()),
        )
        node_scenario = cfg.node_assignments.get(node_id, "normal")
        node.set_scenario(node_scenario)
        nodes.append(node)
    return nodes


# ── Main loop ────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:
    scenario_name = args.scenario
    interval      = args.interval
    duration      = args.duration
    dry_run       = args.dry_run

    cfg = SCENARIOS[scenario_name]
    # Duration from CLI overrides scenario default
    if duration is None:
        duration = cfg.duration_seconds

    nodes = create_nodes(scenario_name)

    logger.info(
        "simulator_starting",
        scenario=scenario_name,
        nodes=[n.node_id for n in nodes],
        interval_s=interval,
        duration_s=duration or "∞",
        dry_run=dry_run,
    )

    # Connect to MQTT (unless dry-run)
    publisher: SimulatorPublisher | None = None
    if not dry_run:
        publisher = SimulatorPublisher()
        publisher.connect()

    # Graceful Ctrl-C
    _running = {"value": True}
    def _handle_sigint(sig, frame):
        logger.info("simulator_stopping", reason="SIGINT")
        _running["value"] = False
    signal.signal(signal.SIGINT, _handle_sigint)

    start_time = time.monotonic()
    reading_count = 0

    try:
        while _running["value"]:
            # Duration check
            if duration is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= duration:
                    logger.info("simulator_duration_reached", elapsed_s=round(elapsed, 1))
                    break

            # Generate and publish one reading per node
            for node in nodes:
                if not _running["value"]:
                    break
                reading = node.generate_reading()
                if dry_run:
                    logger.info(
                        "simulator_dry_run_reading",
                        node_id=reading["node_id"],
                        tilt_x=reading["tilt_x"],
                        tilt_y=reading["tilt_y"],
                        vibration=reading["vibration"],
                        scenario=reading.get("scenario"),
                    )
                elif publisher:
                    publisher.publish(
                        zone_id=node.zone_id,
                        node_id=node.node_id,
                        reading=reading,
                    )
                    logger.info(
                        "published",
                        node_id=node.node_id,
                        zone_id=node.zone_id,
                        tilt_x=round(reading["tilt_x"], 3),
                        tilt_y=round(reading["tilt_y"], 3),
                        vibration=reading["vibration"],
                        scenario=reading.get("scenario"),
                    )
                reading_count += 1

            time.sleep(interval)

    finally:
        if publisher:
            publisher.disconnect()
        logger.info("simulator_stopped", total_readings=reading_count)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    if args.list:
        list_scenarios()
        sys.exit(0)

    run(args)


if __name__ == "__main__":
    main()
