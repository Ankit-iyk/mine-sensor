"""initial_schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-19 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. sensor_readings ───────────────────────────────────────────────────
    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('node_id', sa.String(length=20), nullable=False),
        sa.Column('zone_id', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accel_x', sa.Float(), nullable=False),
        sa.Column('accel_y', sa.Float(), nullable=False),
        sa.Column('accel_z', sa.Float(), nullable=False),
        sa.Column('tilt_x', sa.Float(), nullable=False),
        sa.Column('tilt_y', sa.Float(), nullable=False),
        sa.Column('vibration', sa.Integer(), nullable=False),
        sa.Column('schema_version', sa.String(length=10), server_default='1.0', nullable=False),
        sa.Column('scenario', sa.String(length=50), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sensor_readings_node_time', 'sensor_readings', ['node_id', 'timestamp'])
    op.create_index('ix_sensor_readings_zone_time', 'sensor_readings', ['zone_id', 'timestamp'])

    # Enable TimescaleDB hypertable if TimescaleDB extension is available
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        try:
            op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            op.execute("SELECT create_hypertable('sensor_readings', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);")
        except Exception:
            # If TimescaleDB is not installed or permissions insufficient, standard PG table works fine
            pass

    # ── 2. sensor_features ───────────────────────────────────────────────────
    op.create_table(
        'sensor_features',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('node_id', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tilt_deviation', sa.Float(), nullable=False),
        sa.Column('tilt_rate', sa.Float(), nullable=False),
        sa.Column('vibration_intensity', sa.Float(), nullable=False),
        sa.Column('vibration_frequency', sa.Float(), nullable=False),
        sa.Column('rolling_mean_tilt', sa.Float(), nullable=False),
        sa.Column('rolling_std_tilt', sa.Float(), nullable=False),
        sa.Column('rolling_mean_vib', sa.Float(), nullable=False),
        sa.Column('rolling_std_vib', sa.Float(), nullable=False),
        sa.Column('persistence', sa.Float(), nullable=False),
        sa.Column('trend_slope', sa.Float(), server_default='0.0', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sensor_features_node_time', 'sensor_features', ['node_id', 'timestamp'])

    # ── 3. anomaly_results ───────────────────────────────────────────────────
    op.create_table(
        'anomaly_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('node_id', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('raw_score', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_anomaly_results_node_time', 'anomaly_results', ['node_id', 'timestamp'])

    # ── 4. risk_results ──────────────────────────────────────────────────────
    op.create_table(
        'risk_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('node_id', sa.String(length=20), nullable=False),
        sa.Column('zone_id', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False),
        sa.Column('trend', sa.String(length=20), server_default='STABLE', nullable=False),
        sa.Column('reasons', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_results_node_time', 'risk_results', ['node_id', 'timestamp'])
    op.create_index('ix_risk_results_zone_time', 'risk_results', ['zone_id', 'timestamp'])

    # ── 5. incidents ─────────────────────────────────────────────────────────
    op.create_table(
        'incidents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('node_id', sa.String(length=20), nullable=False),
        sa.Column('zone_id', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('affected_nodes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_incidents_node', 'incidents', ['node_id'])
    op.create_index('ix_incidents_zone_status', 'incidents', ['zone_id', 'status'])


def downgrade() -> None:
    op.drop_table('incidents')
    op.drop_table('risk_results')
    op.drop_table('anomaly_results')
    op.drop_table('sensor_features')
    op.drop_table('sensor_readings')
