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
