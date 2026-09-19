'use client';

import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2, Clock, Check, AlertTriangle } from 'lucide-react';
import { Incident, IncidentStatus, AlertSeverity } from '@/types';

interface IncidentManagerProps {
  incidents: Incident[];
  onResolveIncident: (id: number | string) => Promise<boolean>;
  onSelectNode?: (nodeId: string) => void;
}

export function IncidentManager({ incidents, onResolveIncident, onSelectNode }: IncidentManagerProps) {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [resolvingId, setResolvingId] = useState<number | string | null>(null);

  const filteredIncidents = statusFilter === 'ALL'
    ? incidents
    : incidents.filter((i) => i.status === statusFilter);

  const handleResolve = async (id: number | string) => {
    setResolvingId(id);
    await onResolveIncident(id);
    setResolvingId(null);
  };

  const getSeverityBadgeClass = (sev: AlertSeverity | string) => {
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
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.12)',
              color: '#f87171',
            }}
          >
            <ShieldAlert size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Incident Lifecycle & Resolution
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Debounced geotechnical incidents tracked in database with manual & automated recovery
            </p>
          </div>
        </div>

        {/* Status Filter Tabs */}
        <div
          style={{
            display: 'flex',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '3px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {['ALL', 'ACTIVE', 'RESOLVED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                background: statusFilter === st ? 'var(--bg-surface-elevated)' : 'transparent',
                color: statusFilter === st ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: statusFilter === st ? '1px solid var(--border-light)' : 'none',
                padding: '6px 14px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Incidents Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-light)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>INCIDENT</th>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>LOCATION</th>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>SEVERITY</th>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>RISK</th>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>TRIGGER REASON</th>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>TIMESTAMP</th>
              <th style={{ padding: '10px 14px', fontWeight: 600 }}>STATUS</th>
              <th style={{ padding: '10px 14px', fontWeight: 600, textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filteredIncidents.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No incidents matching the selected filter.
                </td>
              </tr>
            ) : (
              filteredIncidents.map((inc) => {
                const isActive = inc.status === 'ACTIVE';
                const createdTime = new Date(inc.created_at).toLocaleString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                });

                return (
                  <tr
                    key={inc.id}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    {/* ID */}
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-cyan)' }}>
                      #{inc.id}
                    </td>

                    {/* Location */}
                    <td style={{ padding: '12px 14px' }}>
                      <button
                        onClick={() => onSelectNode && onSelectNode(inc.node_id)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-primary)',
                          fontWeight: 700,
                          fontFamily: 'var(--font-mono)',
                          cursor: 'pointer',
                          padding: 0,
                          textDecoration: 'underline',
                          textDecorationColor: 'rgba(255,255,255,0.2)',
                        }}
                      >
                        {inc.node_id}
                      </button>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>
                        {inc.zone_id}
                      </span>
                    </td>

                    {/* Severity */}
                    <td style={{ padding: '12px 14px' }}>
                      <span className={`badge ${getSeverityBadgeClass(inc.severity)}`}>
                        {inc.severity}
                      </span>
                    </td>

                    {/* Risk */}
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: inc.risk_score >= 75 ? '#f43f5e' : '#f59e0b' }}>
                      {inc.risk_score.toFixed(1)}%
                    </td>

                    {/* Trigger Reason */}
                    <td style={{ padding: '12px 14px', color: 'var(--text-secondary)', maxWidth: '300px' }}>
                      {inc.reason}
                    </td>

                    {/* Timestamp */}
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {createdTime}
                    </td>

                    {/* Status */}
                    <td style={{ padding: '12px 14px' }}>
                      <span
                        className={`badge ${
                          isActive ? 'badge-danger animate-danger-flash' : 'badge-safe'
                        }`}
                      >
                        {inc.status}
                      </span>
                    </td>

                    {/* Action */}
                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      {isActive ? (
                        <button
                          onClick={() => handleResolve(inc.id)}
                          disabled={resolvingId === inc.id}
                          className="btn-danger-outline"
                        >
                          {resolvingId === inc.id ? (
                            'Resolving...'
                          ) : (
                            <>
                              <Check size={12} /> Resolve
                            </>
                          )}
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={12} color="#10b981" /> Closed
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
