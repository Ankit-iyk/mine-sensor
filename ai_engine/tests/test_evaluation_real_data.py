import csv

import pytest

from ai_engine.evaluation.real_data import load_real_csv


def test_real_csv_loader_groups_contiguous_hardware_labels(tmp_path):
    path = tmp_path / "hardware.csv"
    fields = [
        "timestamp", "node_id", "tilt_x", "tilt_y",
        "accel_x", "accel_y", "accel_z", "vibration", "label",
    ]
    values = [
        ["2024-01-01T00:00:00+00:00", "N01", 1, 0.8, 0, 0, 9.8, 0, "normal"],
        ["2024-01-01T00:00:01+00:00", "N01", 1.1, 0.8, 0, 0, 9.8, 0, "event"],
        ["2024-01-01T00:00:02+00:00", "N01", 1.2, 0.8, 0, 0, 9.8, 0, "1"],
        ["2024-01-01T00:00:03+00:00", "N01", 1.0, 0.8, 0, 0, 9.8, 0, "normal"],
        ["2024-01-01T00:00:04+00:00", "N01", 1.3, 0.8, 0, 0, 9.8, 0, "anomalous"],
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(values)

    rows = load_real_csv(path)

    assert [row["is_event"] for row in rows] == [False, True, True, False, True]
    assert rows[1]["event_id"] == rows[2]["event_id"]
    assert rows[1]["event_onset_time"] == "2024-01-01T00:00:01+00:00"
    assert rows[4]["event_id"] != rows[1]["event_id"]
    assert rows[4]["timestamp"].isoformat() == "2024-01-01T00:00:04+00:00"
    assert rows[1]["step"] == 1704067201


def test_real_csv_loader_rejects_unknown_labels(tmp_path):
    path = tmp_path / "hardware.csv"
    path.write_text(
        "timestamp,node_id,tilt_x,tilt_y,accel_x,accel_y,accel_z,vibration,label\n"
        "2024-01-01T00:00:00+00:00,N01,1,0.8,0,0,9.8,0,maybe\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported label value"):
        load_real_csv(path)


def test_csv_loader_maps_sensor_aliases_and_event_intervals(tmp_path):
    sensor_path = tmp_path / "sensor.csv"
    sensor_path.write_text(
        "timestamp,tilt_x_deg,tilt_y_deg,accel_x_g,accel_y_g,accel_z_g,vibration,event_label,event_id\n"
        "2026-10-24T00:00:00+00:00,0.1,0.2,0,0,1,0.02,stationary,\n"
        "2026-10-24T00:00:00.100+00:00,0.1,0.2,0,0,1,0.5,tilt,TILT_1\n"
        "2026-10-24T00:00:00.200+00:00,0.1,0.2,0,0,1,0.7,tap,TAP_1\n"
        "2026-10-24T00:00:00.300+00:00,0.1,0.2,0,0,1,0.8,phone_vibration,PHONE_1\n",
        encoding="utf-8",
    )
    event_log_path = tmp_path / "events.csv"
    event_log_path.write_text(
        "event_id,event_type,target_angle_deg,axis,start_timestamp,duration_s,note\n"
        "TILT_1,tilt,0.25,x,2026-10-24T00:00:00.100+00:00,0.1,SYNTHETIC\n"
        "TAP_1,tap,,,2026-10-24T00:00:00.200+00:00,0.1,SYNTHETIC\n"
        "PHONE_1,phone_vibration,,,2026-10-24T00:00:00.300+00:00,0.1,SYNTHETIC\n",
        encoding="utf-8",
    )

    rows = load_real_csv(sensor_path, event_log_path)

    assert [(row["node_id"], row["zone_id"]) for row in rows] == [
        ("N01", "Z01")
    ] * 4
    assert rows[1]["accel_z"] == pytest.approx(9.80665)
    assert rows[1]["vibration"] == 512
    assert [row["event_type"] for row in rows] == [
        "stationary", "tilt", "tap", "phone_vibration",
    ]
    assert [row["is_event"] for row in rows] == [False, True, False, False]
    assert rows[1]["event_id"] == "TILT_1"
    assert rows[1]["event_onset_time"] == "2026-10-24T00:00:00.100000+00:00"
    assert rows[1]["target_angle_deg"] == 0.25
    assert rows[2]["event_id"] == "TAP_1"
    assert rows[3]["event_id"] == "PHONE_1"


def test_csv_loader_accepts_backend_units_and_optional_node_fields(tmp_path):
    path = tmp_path / "sensor.csv"
    path.write_text(
        "timestamp,tilt_x,tilt_y,accel_x,accel_y,accel_z,vibration,label\n"
        "2024-01-01T00:00:00+00:00,1,2,0,0,9.8,100,normal\n",
        encoding="utf-8",
    )

    row = load_real_csv(path)[0]

    assert row["node_id"] == "N01"
    assert row["zone_id"] == "Z01"
    assert row["accel_z"] == pytest.approx(9.8)
    assert row["vibration"] == 100
