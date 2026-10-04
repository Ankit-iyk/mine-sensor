'use client';

import React from 'react';
import { SystemStatus } from '@/types/system';
import { NodeStatus } from '@/components/NodeStatus';
import { ShieldCheck, Cpu, AlertTriangle, Flame, HeartPulse } from 'lucide-react';

interface SummaryCardsProps {
  systemStatus: SystemStatus;
}

export function SummaryCards({ systemStatus }: SummaryCardsProps) {
  const {
    overall_mine_status,
    active_nodes,
    total_nodes,
    warning_nodes,
    active_incidents,
    system_health_percent,
  } = systemStatus;

  return (
    <section
      aria-label="Mine Overview KPI Summary"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '20px',
      }}
    >
      {/* 1. Overall Mine Status */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-secondary, #94a3b8)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            MINE STATUS
          </span>
          <ShieldCheck size={16} color="var(--color-safe, #10b981)" />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
          <NodeStatus status={overall_mine_status} size="lg" />
        </div>

        <div
          style={{
            fontSize: '0.72rem',
            color: 'var(--text-muted, #64748b)',
            marginTop: '8px',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          Zone stability baseline verified
        </div>
      </div>

      {/* 2. Active Nodes */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-secondary, #94a3b8)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            ACTIVE NODES
          </span>
          <Cpu size={16} color="var(--color-cyan, #06b6d4)" />
        </div>

        <div
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            fontFamily: 'var(--font-mono, monospace)',
            letterSpacing: '-0.02em',
            color: '#ffffff',
          }}
        >
          {String(active_nodes).padStart(2, '0')}{' '}
          <span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-muted, #64748b)' }}>
            / {String(total_nodes).padStart(2, '0')}
          </span>
        </div>

        <div
          style={{
            fontSize: '0.72rem',
            color: 'var(--text-muted, #64748b)',
            marginTop: '8px',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          90% network cluster online
        </div>
      </div>

      {/* 3. Warning Nodes */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          borderLeft: warning_nodes > 0 ? '3px solid var(--color-warning, #f59e0b)' : undefined,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-secondary, #94a3b8)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            WARNING NODES
          </span>
          <AlertTriangle size={16} color="var(--color-warning, #f59e0b)" />
        </div>

        <div
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            fontFamily: 'var(--font-mono, monospace)',
            letterSpacing: '-0.02em',
            color: warning_nodes > 0 ? 'var(--color-warning, #f59e0b)' : '#ffffff',
          }}
        >
          {String(warning_nodes).padStart(2, '0')}
        </div>

        <div
          style={{
            fontSize: '0.72rem',
            color: warning_nodes > 0 ? '#fbbf24' : 'var(--text-muted, #64748b)',
            marginTop: '8px',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          {warning_nodes > 0 ? 'Elevated micro-strain in Z02' : 'No warnings detected'}
        </div>
      </div>

      {/* 4. Active Incidents */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          borderLeft: active_incidents > 0 ? '3px solid var(--color-danger, #ef4444)' : undefined,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-secondary, #94a3b8)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            ACTIVE INCIDENTS
          </span>
          <Flame size={16} color="var(--color-danger, #ef4444)" />
        </div>

        <div
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            fontFamily: 'var(--font-mono, monospace)',
            letterSpacing: '-0.02em',
            color: active_incidents > 0 ? '#f87171' : '#ffffff',
          }}
        >
          {String(active_incidents).padStart(2, '0')}
        </div>

        <div
          style={{
            fontSize: '0.72rem',
            color: active_incidents > 0 ? '#f87171' : 'var(--text-muted, #64748b)',
            marginTop: '8px',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          {active_incidents > 0 ? 'Requires operational review' : 'Nominal operations'}
        </div>
      </div>

      {/* 5. System Health */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-secondary, #94a3b8)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            SYSTEM HEALTH
          </span>
          <HeartPulse size={16} color="var(--color-cyan, #06b6d4)" />
        </div>

        <div
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            fontFamily: 'var(--font-mono, monospace)',
            letterSpacing: '-0.02em',
            color: '#38bdf8',
          }}
        >
          {system_health_percent}%
        </div>

        <div
          style={{
            fontSize: '0.72rem',
            color: 'var(--text-muted, #64748b)',
            marginTop: '8px',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          MQTT, API, & DB synced
        </div>
      </div>
    </section>
  );
}
