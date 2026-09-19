'use client';

import React from 'react';
import { Telemetry } from '@/types/telemetry';
import { NodeStatus } from '@/components/NodeStatus';
import { Radio, Gauge, Clock, AlertCircle, Compass } from 'lucide-react';

interface LiveSensorPanelProps {
  telemetry: Telemetry;
  riskScore: number;
  trend: string;
  status?: string;
}

export function LiveSensorPanel({
  telemetry,
  riskScore,
  trend,
  status = 'WARNING',
}: LiveSensorPanelProps) {
  const {
    node_id,
    zone_id,
    tilt_x,
    tilt_y,
    vibration,
    anomaly,
    timestamp,
  } = telemetry;

  return (
    <div
      className="glass-panel"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Gauge size={18} color="var(--color-cyan, #06b6d4)" />
          <h2
            style={{
              fontSize: '0.95rem',
              fontWeight: 700,
              letterSpacing: '0.02em',
              textTransform: 'uppercase',
              color: '#ffffff',
              margin: 0,
            }}
          >
            LIVE SENSOR DATA
          </h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '0.82rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: '#ffffff',
              background: 'rgba(255, 255, 255, 0.08)',
              padding: '2px 8px',
              borderRadius: '4px',
            }}
          >
            Node {node_id}
          </span>
          <span
            style={{
              fontSize: '0.74rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-secondary, #94a3b8)',
            }}
          >
            Zone {zone_id}
          </span>
        </div>
      </div>

      {/* Sensor Metric Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {/* Tilt X */}
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
          }}
        >
          <div
            style={{
              fontSize: '0.7rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-secondary, #94a3b8)',
              marginBottom: '4px',
              textTransform: 'uppercase',
            }}
          >
            Tilt X
          </div>
          <div
            style={{
              fontSize: '1.45rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: Math.abs(tilt_x) > 1.5 ? 'var(--color-warning, #f59e0b)' : '#ffffff',
            }}
          >
            {tilt_x.toFixed(2)}°
          </div>
        </div>

        {/* Tilt Y */}
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
          }}
        >
          <div
            style={{
              fontSize: '0.7rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-secondary, #94a3b8)',
              marginBottom: '4px',
              textTransform: 'uppercase',
            }}
          >
            Tilt Y
          </div>
          <div
            style={{
              fontSize: '1.45rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: Math.abs(tilt_y) > 1.5 ? 'var(--color-warning, #f59e0b)' : '#ffffff',
            }}
          >
            {tilt_y.toFixed(2)}°
          </div>
        </div>

        {/* Vibration */}
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
          }}
        >
          <div
            style={{
              fontSize: '0.7rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-secondary, #94a3b8)',
              marginBottom: '4px',
              textTransform: 'uppercase',
            }}
          >
            Vibration
          </div>
          <div
            style={{
              fontSize: '1.45rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: vibration > 50 ? 'var(--color-warning, #f59e0b)' : '#ffffff',
            }}
          >
            {vibration.toFixed(1)}
          </div>
        </div>

        {/* Anomaly */}
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
          }}
        >
          <div
            style={{
              fontSize: '0.7rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-secondary, #94a3b8)',
              marginBottom: '4px',
              textTransform: 'uppercase',
            }}
          >
            Anomaly
          </div>
          <div
            style={{
              fontSize: '1.45rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: anomaly > 0.7 ? '#f87171' : anomaly > 0.4 ? 'var(--color-warning, #f59e0b)' : 'var(--color-safe, #10b981)',
            }}
          >
            {anomaly.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Risk and Trend Summary Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderRadius: 'var(--radius-sm, 6px)',
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary, #94a3b8)', fontFamily: 'var(--font-mono, monospace)' }}>
            Risk:
          </span>
          <span
            style={{
              fontSize: '1rem',
              fontWeight: 800,
              fontFamily: 'var(--font-mono, monospace)',
              color: riskScore > 50 ? 'var(--color-warning, #f59e0b)' : 'var(--color-safe, #10b981)',
            }}
          >
            {riskScore}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary, #94a3b8)', fontFamily: 'var(--font-mono, monospace)' }}>
            Trend:
          </span>
          <span
            style={{
              fontSize: '0.82rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: trend === 'ESCALATING' ? 'var(--color-warning, #f59e0b)' : '#ffffff',
            }}
          >
            {trend}
          </span>
        </div>
      </div>

      {/* Last Updated Timestamp Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.72rem',
          fontFamily: 'var(--font-mono, monospace)',
          color: 'var(--text-muted, #64748b)',
          marginTop: 'auto',
          paddingTop: '8px',
          borderTop: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={12} />
          <span>Last updated: <strong style={{ color: '#ffffff' }}>{timestamp}</strong></span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Radio size={10} color="#10b981" />
          <span style={{ color: '#10b981' }}>1 Hz Stream</span>
        </div>
      </div>
    </div>
  );
}
