'use client';

import React from 'react';
import { Incident } from '@/types/incident';
import { NodeStatus } from '@/components/NodeStatus';
import { Flame, Clock, ChevronRight, AlertTriangle } from 'lucide-react';

interface ActiveIncidentsProps {
  incidents: Incident[];
  selectedNodeId?: string;
  onSelectNode: (nodeId: string) => void;
}

export function ActiveIncidents({
  incidents,
  selectedNodeId,
  onSelectNode,
}: ActiveIncidentsProps) {
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
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Flame size={18} color="var(--color-danger, #ef4444)" />
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
            ACTIVE INCIDENTS
          </h2>
        </div>

        <span
          style={{
            fontSize: '0.72rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--text-secondary, #94a3b8)',
            background: 'rgba(255, 255, 255, 0.06)',
            padding: '2px 8px',
            borderRadius: '4px',
          }}
        >
          {incidents.length} UNRESOLVED
        </span>
      </div>

      {/* Incidents List */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          overflowY: 'auto',
          maxHeight: '230px',
        }}
      >
        {incidents.length === 0 ? (
          <div
            style={{
              padding: '30px 16px',
              textAlign: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.2)',
              borderRadius: 'var(--radius-sm, 6px)',
              border: '1px dashed var(--border-subtle, rgba(255,255,255,0.08))',
              color: 'var(--text-muted, #64748b)',
              fontFamily: 'var(--font-mono, monospace)',
              fontSize: '0.82rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ color: 'var(--color-safe, #10b981)', fontWeight: 600 }}>
              NO ACTIVE INCIDENTS
            </span>
            <span style={{ fontSize: '0.72rem' }}>All mine zones operating nominally</span>
          </div>
        ) : (
          incidents.map((incident) => {
            const isSelected = incident.node_id === selectedNodeId;
            const isDanger = incident.severity === 'CRITICAL' || incident.risk_score >= 70;

          return (
            <div
              key={incident.id}
              onClick={() => onSelectNode(incident.node_id)}
              tabIndex={0}
              role="button"
              aria-label={`Incident ${incident.id} on node ${incident.node_id}`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onSelectNode(incident.node_id);
                }
              }}
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm, 6px)',
                backgroundColor: isSelected
                  ? 'rgba(255, 255, 255, 0.08)'
                  : 'rgba(0, 0, 0, 0.3)',
                border: isSelected
                  ? '1px solid var(--border-light, rgba(255,255,255,0.25))'
                  : '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
                borderLeft: isDanger
                  ? '3px solid #ef4444'
                  : '3px solid #f59e0b',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '6px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono, monospace)',
                      color: isDanger ? '#f87171' : '#fbbf24',
                    }}
                  >
                    <AlertTriangle size={12} />
                    {incident.severity}
                  </span>

                  <span
                    style={{
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono, monospace)',
                      color: '#ffffff',
                    }}
                  >
                    Node {incident.node_id}
                  </span>

                  <span
                    style={{
                      fontSize: '0.72rem',
                      color: 'var(--text-muted, #64748b)',
                      fontFamily: 'var(--font-mono, monospace)',
                    }}
                  >
                    Zone {incident.zone_id}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono, monospace)',
                      color: '#f8fafc',
                    }}
                  >
                    Risk: <strong style={{ color: isDanger ? '#f87171' : '#fbbf24' }}>{incident.risk_score}</strong>
                  </span>
                  <ChevronRight size={14} color="var(--text-muted, #64748b)" />
                </div>
              </div>

              {/* Bottom details: Trend & Time */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.7rem',
                  fontFamily: 'var(--font-mono, monospace)',
                  color: 'var(--text-secondary, #94a3b8)',
                }}
              >
                <div>
                  Trend:{' '}
                  <strong
                    style={{
                      color:
                        incident.trend === 'ESCALATING'
                          ? '#f59e0b'
                          : incident.trend === 'PERSISTENT'
                          ? '#fbbf24'
                          : '#94a3b8',
                    }}
                  >
                    {incident.trend}
                  </strong>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted, #64748b)' }}>
                  <Clock size={11} />
                  <span>{incident.created_at}</span>
                </div>
              </div>
            </div>
          );
        }))}
      </div>
    </div>
  );
}
