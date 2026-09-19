'use client';

import React, { useState } from 'react';
import { TrendingUp, TrendingDown, Minus, ChevronRight, Gauge } from 'lucide-react';
import { LegacyNodeStatus as NodeStatus } from '@/types';

interface RiskGaugeGridProps {
  nodes: Record<string, NodeStatus>;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}

export function RiskGaugeGrid({ nodes, selectedNodeId, onSelectNode }: RiskGaugeGridProps) {
  const [zoneFilter, setZoneFilter] = useState<string>('ALL');

  const nodeList = Object.values(nodes);
  const filteredNodes = zoneFilter === 'ALL'
    ? nodeList
    : nodeList.filter((n) => n.zone_id === zoneFilter);

  const zones = ['ALL', 'ZONE_A', 'ZONE_B', 'ZONE_C'];

  const getStrokeColor = (score: number) => {
    if (score >= 75) return '#f43f5e';
    if (score >= 45) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Header and Zone Filter */}
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
              background: 'rgba(6, 182, 212, 0.12)',
              color: 'var(--color-cyan)',
            }}
          >
            <Gauge size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Geotechnical Risk Gauges
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Fused Kalman & ML Stability Index across instrumented drift points
            </p>
          </div>
        </div>

        {/* Zone Filter Tabs */}
        <div
          style={{
            display: 'flex',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '3px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {zones.map((zone) => (
            <button
              key={zone}
              onClick={() => setZoneFilter(zone)}
              style={{
                background: zoneFilter === zone ? 'var(--bg-surface-elevated)' : 'transparent',
                color: zoneFilter === zone ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: zoneFilter === zone ? '1px solid var(--border-light)' : 'none',
                padding: '6px 14px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {zone === 'ALL' ? 'All Zones' : zone.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Gauges */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))',
          gap: '16px',
        }}
      >
        {filteredNodes.map((node) => {
          const isSelected = selectedNodeId === node.node_id;
          const strokeColor = getStrokeColor(node.latest_risk);
          
          // Circular SVG parameters
          const radius = 38;
          const circumference = 2 * Math.PI * radius;
          const strokeDashoffset = circumference - (node.latest_risk / 100) * circumference;

          return (
            <div
              key={node.node_id}
              onClick={() => onSelectNode(node.node_id)}
              className="glass-panel"
              style={{
                padding: '18px',
                background: isSelected ? 'var(--bg-glass-hover)' : 'rgba(17, 24, 39, 0.65)',
                borderColor: isSelected ? 'var(--color-cyan)' : node.state === 'DANGER' ? 'var(--color-danger-border)' : 'var(--border-subtle)',
                cursor: 'pointer',
                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                boxShadow: isSelected ? '0 0 20px rgba(6, 182, 212, 0.25)' : 'none',
                transform: isSelected ? 'translateY(-2px)' : 'none',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {node.node_id}
                    </span>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                      {node.zone_id}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Depth: -{node.depth_m}m • Grade: {node.stability_grade}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    className={`badge ${
                      node.state === 'DANGER' ? 'badge-danger' : node.state === 'WARNING' ? 'badge-warning' : 'badge-safe'
                    }`}
                  >
                    {node.state}
                  </span>
                </div>
              </div>

              {/* Middle section: Circular Gauge + Metrics */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
                {/* SVG Radial Progress Gauge */}
                <div style={{ position: 'relative', width: '92px', height: '92px', flexShrink: 0 }}>
                  <svg width="92" height="92" style={{ transform: 'rotate(-90deg)' }}>
                    {/* Background Track */}
                    <circle
                      cx="46"
                      cy="46"
                      r={radius}
                      stroke="rgba(255, 255, 255, 0.08)"
                      strokeWidth="7"
                      fill="transparent"
                    />
                    {/* Animated Progress Ring */}
                    <circle
                      cx="46"
                      cy="46"
                      r={radius}
                      stroke={strokeColor}
                      strokeWidth="7"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                      fill="transparent"
                      style={{
                        transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s ease',
                      }}
                    />
                  </svg>
                  {/* Gauge Center Text */}
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '1.25rem',
                        fontWeight: 800,
                        color: strokeColor,
                      }}
                    >
                      {node.latest_risk.toFixed(0)}
                    </span>
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Risk
                    </span>
                  </div>
                </div>

                {/* Telemetry Breakdown */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Tilt Velocity</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>
                      {node.tilt_rate >= 0 ? `+${node.tilt_rate.toFixed(3)}` : node.tilt_rate.toFixed(3)}°/s
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Vib. Intensity</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>
                      {node.vibration_intensity} <span style={{ color: 'var(--text-muted)' }}>ADC</span>
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Vector Trend</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600, fontSize: '0.72rem', color: node.trend === 'INCREASING' ? 'var(--color-danger)' : node.trend === 'DECREASING' ? 'var(--color-safe)' : 'var(--text-secondary)' }}>
                      {node.trend === 'INCREASING' && <TrendingUp size={13} />}
                      {node.trend === 'DECREASING' && <TrendingDown size={13} />}
                      {node.trend === 'STABLE' && <Minus size={13} />}
                      {node.trend}
                    </span>
                  </div>
                </div>
              </div>

              {/* Bottom footer button */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '14px',
                  paddingTop: '10px',
                  borderTop: '1px solid var(--border-subtle)',
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                }}
              >
                <span>{node.precursor_stage.replace('STAGE_', 'Stg ')}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '2px', color: 'var(--color-cyan)', fontWeight: 600 }}>
                  Inspect <ChevronRight size={13} />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
