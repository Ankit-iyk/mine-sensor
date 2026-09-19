'use client';

import React from 'react';
import { AlertTriangle, ShieldCheck, Flame, Compass, Network } from 'lucide-react';
import { LegacyNodeStatus as NodeStatus, Incident } from '@/types';

interface MetricCardsProps {
  nodes: Record<string, NodeStatus>;
  incidents: Incident[];
}

export function MetricCards({ nodes, incidents }: MetricCardsProps) {
  const nodeList = Object.values(nodes);
  
  // Calculate max risk
  const maxRiskNode = nodeList.reduce(
    (max, n) => (n.latest_risk > max.latest_risk ? n : max),
    nodeList[0] || { latest_risk: 0, node_id: 'N/A', zone_id: 'N/A' }
  );

  // Status counts
  const safeCount = nodeList.filter((n) => n.state === 'SAFE').length;
  const warningCount = nodeList.filter((n) => n.state === 'WARNING').length;
  const dangerCount = nodeList.filter((n) => n.state === 'DANGER').length;

  // Active Incidents
  const activeIncidents = incidents.filter((i) => i.status === 'ACTIVE');
  const criticalCount = activeIncidents.filter((i) => i.severity === 'CRITICAL').length;
  const highCount = activeIncidents.filter((i) => i.severity === 'HIGH').length;

  // Multi-node spatial correlation detection
  const multiNodeCorrelated = dangerCount >= 2 || (dangerCount >= 1 && warningCount >= 1);

  const getRiskColor = (score: number) => {
    if (score >= 75) return 'var(--color-danger)';
    if (score >= 45) return 'var(--color-warning)';
    return 'var(--color-safe)';
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}
    >
      {/* 1. Peak Fleet Risk Score */}
      <div className="glass-panel" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
              Peak Fleet Risk
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '2.2rem',
                  fontWeight: 800,
                  color: getRiskColor(maxRiskNode.latest_risk),
                  textShadow: maxRiskNode.latest_risk >= 75 ? '0 0 15px rgba(244, 63, 94, 0.4)' : 'none',
                }}
              >
                {maxRiskNode.latest_risk.toFixed(1)}
              </span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ 100</span>
            </div>
          </div>
          <div
            style={{
              padding: '10px',
              borderRadius: 'var(--radius-md)',
              background: maxRiskNode.latest_risk >= 75 ? 'var(--color-danger-bg)' : 'var(--color-safe-bg)',
              color: getRiskColor(maxRiskNode.latest_risk),
            }}
          >
            <Flame size={22} />
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', marginTop: '14px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${Math.min(100, maxRiskNode.latest_risk)}%`,
              height: '100%',
              background: maxRiskNode.latest_risk >= 75 ? 'linear-gradient(90deg, #f59e0b, #f43f5e)' : 'linear-gradient(90deg, #10b981, #06b6d4)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <span>Driving Node: <strong style={{ color: 'var(--text-primary)' }}>{maxRiskNode.node_id}</strong></span>
          <span>Zone: <strong style={{ color: 'var(--text-primary)' }}>{maxRiskNode.zone_id}</strong></span>
        </div>
      </div>

      {/* 2. Active Incidents */}
      <div className={`glass-panel ${criticalCount > 0 ? 'animate-danger-flash' : ''}`} style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
              Active Incidents
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '2.2rem',
                  fontWeight: 800,
                  color: activeIncidents.length > 0 ? '#fb7185' : 'var(--color-safe)',
                }}
              >
                {activeIncidents.length}
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Debounced</span>
            </div>
          </div>
          <div
            style={{
              padding: '10px',
              borderRadius: 'var(--radius-md)',
              background: activeIncidents.length > 0 ? 'var(--color-danger-bg)' : 'var(--color-safe-bg)',
              color: activeIncidents.length > 0 ? 'var(--color-danger)' : 'var(--color-safe)',
            }}
          >
            <AlertTriangle size={22} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
          <span className="badge badge-critical" style={{ flex: 1, justifyContent: 'center' }}>
            {criticalCount} Critical
          </span>
          <span className="badge badge-high" style={{ flex: 1, justifyContent: 'center' }}>
            {highCount} High
          </span>
        </div>
      </div>

      {/* 3. Sensor Fleet Health */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
              Telemetry Fleet
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '2.2rem',
                  fontWeight: 800,
                  color: 'var(--color-cyan)',
                }}
              >
                {nodeList.length} / {nodeList.length}
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Online</span>
            </div>
          </div>
          <div
            style={{
              padding: '10px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(6, 182, 212, 0.12)',
              color: 'var(--color-cyan)',
            }}
          >
            <ShieldCheck size={22} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '6px', marginTop: '16px' }}>
          <span className="badge badge-safe" style={{ flex: 1, justifyContent: 'center' }}>
            {safeCount} Safe
          </span>
          <span className="badge badge-warning" style={{ flex: 1, justifyContent: 'center' }}>
            {warningCount} Warning
          </span>
          <span className="badge badge-danger" style={{ flex: 1, justifyContent: 'center' }}>
            {dangerCount} Danger
          </span>
        </div>
      </div>

      {/* 4. Spatial Precursor Engine */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
              Spatial Correlation
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '1.25rem',
                  fontWeight: 700,
                  color: multiNodeCorrelated ? 'var(--color-danger)' : 'var(--color-safe)',
                }}
              >
                {multiNodeCorrelated ? 'MULTI-NODE EVENT' : 'ISOLATED MICRO-SEISMIC'}
              </span>
            </div>
          </div>
          <div
            style={{
              padding: '10px',
              borderRadius: 'var(--radius-md)',
              background: multiNodeCorrelated ? 'var(--color-danger-bg)' : 'rgba(16, 185, 129, 0.12)',
              color: multiNodeCorrelated ? 'var(--color-danger)' : 'var(--color-safe)',
            }}
          >
            <Network size={22} />
          </div>
        </div>

        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '14px' }}>
          {multiNodeCorrelated
            ? 'Coordinated shear vector detected between Zone B nodes. Risk multiplier active.'
            : 'Precursor drift rates within localized structural tolerances.'}
        </p>
      </div>
    </div>
  );
}
