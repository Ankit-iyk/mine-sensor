'use client';

import React, { useState } from 'react';
import { Radio, AlertOctagon, ShieldAlert, CheckCircle2, Filter, Trash2 } from 'lucide-react';
import { AlertEvent, AlertSeverity } from '@/types';

interface AlertLiveFeedProps {
  alerts: AlertEvent[];
  onClearAlerts?: () => void;
  onSelectNode?: (nodeId: string) => void;
}

export function AlertLiveFeed({ alerts, onClearAlerts, onSelectNode }: AlertLiveFeedProps) {
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  const filteredAlerts = severityFilter === 'ALL'
    ? alerts
    : alerts.filter((a) => a.severity === severityFilter);

  const getSeverityBadgeClass = (sev: AlertSeverity) => {
    switch (sev) {
      case 'CRITICAL':
        return 'badge-critical';
      case 'HIGH':
        return 'badge-high';
      case 'MEDIUM':
        return 'badge-medium';
      case 'LOW':
        return 'badge-low';
      default:
        return 'badge-safe';
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: '540px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(244, 63, 94, 0.12)',
              color: 'var(--color-danger)',
            }}
          >
            <Radio size={20} className="animate-pulse-glow" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Live WebSocket Alert Stream
              </h2>
              <span className="badge badge-critical" style={{ fontSize: '0.68rem' }}>
                {alerts.length} Captured
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Real-time push from <code style={{ color: 'var(--color-cyan)', fontFamily: 'var(--font-mono)' }}>/ws/alerts</code>
            </p>
          </div>
        </div>

        {/* Severity Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--border-light)',
              color: 'var(--text-primary)',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="MEDIUM">Medium Only</option>
            <option value="LOW">Low Only</option>
          </select>

          {onClearAlerts && alerts.length > 0 && (
            <button
              onClick={onClearAlerts}
              className="btn-secondary"
              style={{ padding: '6px 8px' }}
              title="Clear captured stream"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Stream List container */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          paddingRight: '6px',
        }}
      >
        {filteredAlerts.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--text-muted)',
              textAlign: 'center',
              padding: '40px 20px',
            }}
          >
            <CheckCircle2 size={36} color="#10b981" style={{ marginBottom: '12px', opacity: 0.8 }} />
            <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              No Active Alerts in Buffer
            </p>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px', maxWidth: '280px' }}>
              Subsurface precursor signals are steady. Alerts will stream instantly as the debouncer fires.
            </p>
          </div>
        ) : (
          filteredAlerts.map((alert, idx) => {
            const timeStr = new Date(alert.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            });

            return (
              <div
                key={alert.event_id || idx}
                className="animate-slide-up"
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: `1px solid ${
                    alert.severity === 'CRITICAL'
                      ? 'rgba(239, 68, 68, 0.45)'
                      : alert.severity === 'HIGH'
                      ? 'rgba(249, 115, 22, 0.4)'
                      : 'var(--border-subtle)'
                  }`,
                  borderRadius: 'var(--radius-md)',
                  padding: '12px 16px',
                  boxShadow: alert.severity === 'CRITICAL' ? '0 0 15px rgba(239, 68, 68, 0.15)' : 'none',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`badge ${getSeverityBadgeClass(alert.severity)}`}>
                      {alert.severity}
                    </span>
                    <button
                      onClick={() => onSelectNode && onSelectNode(alert.node_id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--color-electric)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      {alert.node_id}
                    </button>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      • {alert.zone_id}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    <span>{timeStr}</span>
                    <span style={{ color: 'var(--color-cyan)', fontWeight: 600 }}>
                      Risk {alert.risk_score.toFixed(0)}%
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {alert.reason}
                </p>

                {alert.affected_nodes && alert.affected_nodes.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '8px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Affected Neighbors:</span>
                    {alert.affected_nodes.map((n) => (
                      <span
                        key={n}
                        style={{
                          fontSize: '0.68rem',
                          fontFamily: 'var(--font-mono)',
                          background: 'rgba(255,255,255,0.06)',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          color: 'var(--text-primary)',
                        }}
                      >
                        {n}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
