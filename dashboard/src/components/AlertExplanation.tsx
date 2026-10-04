'use client';

import React from 'react';
import { AlertExplanation as AlertExplanationType } from '@/types/explanation';
import { HelpCircle, CheckCircle2, AlertTriangle, ShieldCheck, ArrowUpRight } from 'lucide-react';

interface AlertExplanationProps {
  explanation: AlertExplanationType;
}

export function AlertExplanation({ explanation }: AlertExplanationProps) {
  const { node_id, zone_id, risk_score, trend, status, title, reasons, metrics_summary } = explanation;

  const isWarningOrDanger = status === 'WARNING' || status === 'DANGER' || risk_score >= 40;

  return (
    <section
      aria-label="Explainable Alert Diagnostics"
      className="glass-panel"
      style={{
        padding: '20px 24px',
        borderLeft: isWarningOrDanger
          ? '4px solid var(--color-warning, #f59e0b)'
          : '4px solid var(--color-safe, #10b981)',
      }}
    >
      {/* Title Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {isWarningOrDanger ? (
            <AlertTriangle size={20} color="var(--color-warning, #f59e0b)" />
          ) : (
            <ShieldCheck size={20} color="var(--color-safe, #10b981)" />
          )}

          <div>
            <h2
              style={{
                fontSize: '1rem',
                fontWeight: 800,
                letterSpacing: '0.03em',
                color: '#ffffff',
                margin: 0,
                textTransform: 'uppercase',
              }}
            >
              {title}
            </h2>
            <p
              style={{
                fontSize: '0.74rem',
                color: 'var(--text-secondary, #94a3b8)',
                marginTop: '2px',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              Diagnostic Root-Cause Analysis for Node {node_id} (Zone {zone_id || 'Z02'})
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              fontSize: '0.74rem',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-secondary, #94a3b8)',
              background: 'rgba(0, 0, 0, 0.3)',
              padding: '4px 10px',
              borderRadius: '4px',
              border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
            }}
          >
            Risk: <strong style={{ color: isWarningOrDanger ? '#fbbf24' : '#34d399' }}>{risk_score}</strong> | Trend: <strong style={{ color: '#ffffff' }}>{trend}</strong>
          </div>
        </div>
      </div>

      {/* Subtitle / Prompt Header */}
      <div
        style={{
          fontSize: '0.8rem',
          fontWeight: 600,
          color: 'var(--text-secondary, #94a3b8)',
          marginBottom: '12px',
          fontFamily: 'var(--font-mono, monospace)',
        }}
      >
        {isWarningOrDanger ? 'Risk increased because:' : 'Stability confirmed because:'}
      </div>

      {/* Reasons List (Data-driven, not hardcoded in JSX) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '10px',
        }}
      >
        {reasons.map((reason, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm, 6px)',
              backgroundColor: 'rgba(0, 0, 0, 0.35)',
              border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
            }}
          >
            <CheckCircle2
              size={15}
              color={isWarningOrDanger ? 'var(--color-warning, #f59e0b)' : 'var(--color-safe, #10b981)'}
              style={{ marginTop: '2px', flexShrink: 0 }}
            />
            <span
              style={{
                fontSize: '0.82rem',
                color: 'var(--text-primary, #f8fafc)',
                lineHeight: 1.4,
              }}
            >
              {reason}
            </span>
          </div>
        ))}
      </div>

      {/* Structured Metrics Summary if available */}
      {metrics_summary && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
            marginTop: '14px',
            paddingTop: '12px',
            borderTop: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
            fontSize: '0.72rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--text-muted, #64748b)',
          }}
        >
          {metrics_summary.tilt_deviation && (
            <div>
              Tilt Variance: <span style={{ color: '#ffffff' }}>{metrics_summary.tilt_deviation}</span>
            </div>
          )}
          {metrics_summary.vibration_level && (
            <div>
              Vibration Level: <span style={{ color: '#ffffff' }}>{metrics_summary.vibration_level}</span>
            </div>
          )}
          {metrics_summary.risk_velocity && (
            <div>
              Escalation Rate: <span style={{ color: 'var(--color-warning, #f59e0b)' }}>{metrics_summary.risk_velocity}</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
