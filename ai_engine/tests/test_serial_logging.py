import csv
from pathlib import Path

from tools.log_serial_to_csv import (
    attach_labels,
    load_label_intervals,
    read_json_lines,
    write_csv,
)


def test_serial_sample_maps_schema_and_attaches_event_labels(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    sample = repo_root / "ai_engine" / "tests" / "fixtures" / "serial_sample.jsonl"
    records = read_json_lines(sample.read_text(encoding="utf-8").splitlines())
    assert len(records) == 3
    assert records[0]["accel_z"] == 9.8
    assert records[1]["accel_x"] == 0.0

    label_file = tmp_path / "labels.csv"
    label_file.write_text(
        "event_id,node_id,start_time,end_time,event_type,true_angle_deg\n"
        "tilt-1,N01,2026-10-24T08:00:01+00:00,2026-10-24T08:00:01+00:00,tilt_step,1.0\n",
        encoding="utf-8",
    )
    labelled = attach_labels(records, load_label_intervals(label_file))
    output = tmp_path / "readings.csv"
    write_csv(output, labelled)
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["label"] for row in rows] == ["0", "1", "0"]
    assert list(rows[0]) == [
        "timestamp", "node_id", "tilt_x", "tilt_y", "accel_x",
        "accel_y", "accel_z", "vibration", "label",
    ]
