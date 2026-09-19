import os

from ai_engine.pipeline.build_training_data import (
    FEATURE_COLUMNS,
    build_normal_feature_dataset,
    save_dataset_csv,
)


def test_build_dataset_produces_rows_for_all_nodes():
    rows = build_normal_feature_dataset(node_ids=["N01", "N02"], count_per_node=10)
    assert len(rows) == 20
    assert {row["node_id"] for row in rows} == {"N01", "N02"}


def test_build_dataset_rows_have_all_feature_columns():
    rows = build_normal_feature_dataset(node_ids=["N01"], count_per_node=5)
    for column in FEATURE_COLUMNS:
        assert column in rows[0]


def test_save_dataset_csv_creates_file(tmp_path):
    rows = build_normal_feature_dataset(node_ids=["N01"], count_per_node=5)
    output_path = str(tmp_path / "test_output.csv")
    result_path = save_dataset_csv(rows, path=output_path)
    assert os.path.exists(result_path)
