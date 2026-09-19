'use client';

import React, { useState } from 'react';
import { Map, Layers, Eye, ShieldAlert, Sparkles } from 'lucide-react';
import { LegacyNodeStatus as NodeStatus } from '@/types';

interface MineZoneMapProps {
  nodes: Record<string, NodeStatus>;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}

export function MineZoneMap({ nodes, selectedNodeId, onSelectNode }: MineZoneMapProps) {
  const [showContours, setShowContours] = useState<boolean>(true);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const nodeList = Object.values(nodes);

  // Determine if spatial correlation link exists
  const node3 = nodes['NODE_03'];
  const node4 = nodes['NODE_04'];
  const hasCorrelation = node3 && node4 && (node3.state === 'WARNING' || node3.state === 'DANGER') && (node4.state === 'WARNING' || node4.state === 'DANGER');

  const getNodeColor = (state: string) => {
    switch (state) {
      case 'DANGER':
        return '#f43f5e';
      case 'WARNING':
        return '#f59e0b';
      case 'SAFE':
      default:
        return '#10b981';
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
          marginBottom: '18px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(56, 189, 248, 0.12)',
              color: 'var(--color-electric)',
            }}
          >
            <Map size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Geological Subsurface Spatial Twin
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Cross-sectional drift topology, telemetry nodes, and spatial shear precursor vectors
            </p>
          </div>
        </div>

        {/* Map View Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setShowContours(!showContours)}
            className="btn-secondary"
            style={{
              background: showContours ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255,255,255,0.05)',
              borderColor: showContours ? 'rgba(56, 189, 248, 0.4)' : 'var(--border-subtle)',
              color: showContours ? 'var(--color-electric)' : 'var(--text-secondary)',
            }}
          >
            <Layers size={13} />
            {showContours ? 'Strain Heatmap On' : 'Strain Heatmap Off'}
          </button>
        </div>
      </div>

      {/* SVG Canvas Map */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '420px',
          background: 'radial-gradient(ellipse at 50% 60%, #0e1526 0%, #080b12 100%)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-light)',
          overflow: 'hidden',
        }}
      >
        {/* SVG Topography & Mine Drifts */}
        <svg
          viewBox="0 0 900 420"
          style={{ width: '100%', height: '100%', display: 'block' }}
          preserveAspectRatio="none"
        >
          <defs>
            {/* Strain Gradient for Zone B */}
            <radialGradient id="strainGlow" cx="62%" cy="60%" r="28%">
              <stop offset="0%" stopColor="rgba(244, 63, 94, 0.35)" />
              <stop offset="60%" stopColor="rgba(245, 158, 11, 0.12)" />
              <stop offset="100%" stopColor="rgba(244, 63, 94, 0)" />
            </radialGradient>

            {/* Geological strata pattern */}
            <pattern id="strataGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.025)" strokeWidth="1" />
            </pattern>

            {/* Pulsing glow filter */}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background Grid */}
          <rect width="900" height="420" fill="url(#strataGrid)" />

          {/* Surface Topography Line */}
          <path
            d="M 0 50 Q 200 40 450 55 T 900 45 L 900 0 L 0 0 Z"
            fill="rgba(15, 23, 42, 0.6)"
            stroke="rgba(255, 255, 255, 0.15)"
            strokeWidth="1.5"
          />
          <text x="30" y="32" fill="#64748b" fontSize="11" fontFamily="var(--font-mono)">
            SURFACE LEVEL (0m EL)
          </text>

          {/* Geological Fault Line (Subsidence Threat Plane) */}
          <path
            d="M 500 50 Q 560 180 630 380"
            fill="none"
            stroke="rgba(239, 68, 68, 0.35)"
            strokeWidth="2"
            strokeDasharray="4 6"
          />
          <text x="640" y="360" fill="#f87171" fontSize="10" fontFamily="var(--font-mono)">
            ACTIVE SHEAR FAULT F-4
          </text>

          {/* Vertical Main Shaft */}
          <line
            x1="120"
            y1="50"
            x2="120"
            y2="380"
            stroke="rgba(255, 255, 255, 0.2)"
            strokeWidth="5"
          />
          <text x="135" y="90" fill="#94a3b8" fontSize="11" fontFamily="var(--font-mono)">
            SHAFT ALPHA
          </text>

          {/* Level 1: Drift A (-120m to -150m) */}
          <path
            d="M 120 130 L 480 145"
            fill="none"
            stroke="rgba(6, 182, 212, 0.4)"
            strokeWidth="7"
            strokeLinecap="round"
          />
          <text x="150" y="120" fill="var(--color-cyan)" fontSize="11" fontWeight="600" fontFamily="var(--font-mono)">
            ZONE A • DRIFT LEVEL 1 (-130m)
          </text>

          {/* Level 2: Drift B (-210m to -240m) */}
          <path
            d="M 120 230 L 700 245"
            fill="none"
            stroke="rgba(245, 158, 11, 0.4)"
            strokeWidth="9"
            strokeLinecap="round"
          />
          <text x="150" y="218" fill="var(--color-warning)" fontSize="11" fontWeight="600" fontFamily="var(--font-mono)">
            ZONE B • DRIFT LEVEL 2 (-230m) [ELEVATED STRESS]
          </text>

          {/* Level 3: Drift C (-310m to -350m) */}
          <path
            d="M 120 330 L 820 350"
            fill="none"
            stroke="rgba(16, 185, 129, 0.35)"
            strokeWidth="7"
            strokeLinecap="round"
          />
          <text x="150" y="320" fill="var(--color-safe)" fontSize="11" fontWeight="600" fontFamily="var(--font-mono)">
            ZONE C • DEEP SUB-LEVEL (-340m)
          </text>

          {/* Strain Heatmap Layer around Zone B if enabled */}
          {showContours && (
            <ellipse cx="560" cy="235" rx="190" ry="85" fill="url(#strainGlow)" />
          )}

          {/* Spatial Correlation Vector Line between Node 03 and Node 04 */}
          {hasCorrelation && (
            <g>
              <line
                x1={nodes['NODE_03'] ? (nodes['NODE_03'].x / 100) * 900 : 495}
                y1={nodes['NODE_03'] ? (nodes['NODE_03'].y / 100) * 420 : 243}
                x2={nodes['NODE_04'] ? (nodes['NODE_04'].x / 100) * 900 : 612}
                y2={nodes['NODE_04'] ? (nodes['NODE_04'].y / 100) * 420 : 273}
                stroke="#f43f5e"
                strokeWidth="3"
                strokeDasharray="6 4"
                filter="url(#glow)"
              />
              <rect
                x="510"
                y="205"
                width="150"
                height="22"
                rx="4"
                fill="rgba(244, 63, 94, 0.25)"
                stroke="rgba(244, 63, 94, 0.7)"
              />
              <text x="520" y="220" fill="#ffffff" fontSize="9" fontWeight="700" fontFamily="var(--font-mono)">
                SPATIAL SHEAR VECTOR
              </text>
            </g>
          )}

          {/* Sensor Nodes Markers */}
          {nodeList.map((node) => {
            const cx = (node.x / 100) * 900;
            const cy = (node.y / 100) * 420;
            const color = getNodeColor(node.state);
            const isSelected = selectedNodeId === node.node_id;
            const isHovered = hoveredNodeId === node.node_id;

            return (
              <g
                key={node.node_id}
                onClick={() => onSelectNode(node.node_id)}
                onMouseEnter={() => setHoveredNodeId(node.node_id)}
                onMouseLeave={() => setHoveredNodeId(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Danger pulsing halo */}
                {node.state === 'DANGER' && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isSelected || isHovered ? 26 : 20}
                    fill="none"
                    stroke="#f43f5e"
                    strokeWidth="1.5"
                    opacity="0.7"
                    className="animate-pulse-glow"
                  />
                )}

                {/* Outer Ring */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isSelected || isHovered ? 15 : 12}
                  fill="#0e1420"
                  stroke={isSelected ? '#38bdf8' : color}
                  strokeWidth={isSelected ? 3 : 2}
                  filter={isSelected || node.state === 'DANGER' ? 'url(#glow)' : undefined}
                />

                {/* Inner Core */}
                <circle cx={cx} cy={cy} r={isSelected || isHovered ? 7 : 5} fill={color} />

                {/* Label */}
                <text
                  x={cx}
                  y={cy - 18}
                  fill={isSelected ? '#38bdf8' : '#f8fafc'}
                  fontSize="11"
                  fontWeight={isSelected ? '800' : '600'}
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                >
                  {node.node_id}
                </text>

                {/* Mini Risk Badge */}
                <rect
                  x={cx - 18}
                  y={cy + 16}
                  width="36"
                  height="16"
                  rx="3"
                  fill="rgba(0, 0, 0, 0.75)"
                  stroke={color}
                  strokeWidth="1"
                />
                <text
                  x={cx}
                  y={cy + 28}
                  fill={color}
                  fontSize="9.5"
                  fontWeight="700"
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                >
                  {node.latest_risk.toFixed(0)}%
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend Overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '14px',
            background: 'rgba(10, 15, 26, 0.85)',
            backdropFilter: 'blur(8px)',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            fontSize: '0.72rem',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
            SAFE (&lt;45)
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
            WARNING (45–74)
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f43f5e' }} />
            DANGER (&ge;75)
          </div>
        </div>

        {/* Subsurface Notice */}
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '14px',
            background: 'rgba(10, 15, 26, 0.85)',
            backdropFilter: 'blur(8px)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          DEPTH RANGE: 0m to -380m • BOREHOLE GRID: 40m
        </div>
      </div>
    </div>
  );
}
