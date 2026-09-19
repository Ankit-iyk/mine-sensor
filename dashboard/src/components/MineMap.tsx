'use client';

import React from 'react';
import { MineNode } from '@/types/node';
import { NodeStatus } from '@/components/NodeStatus';
import { getStatusConfig } from '@/lib/status-config';
import { Compass, Layers, Info, MapPin } from 'lucide-react';

interface MineMapProps {
  nodes: Record<string, MineNode>;
  selectedNodeId: string;
  onSelectNode: (nodeId: string) => void;
}

export function MineMap({ nodes, selectedNodeId, onSelectNode }: MineMapProps) {
  const nodeList = Object.values(nodes);
  const selectedNode = nodes[selectedNodeId] || nodeList[0];

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
      {/* Map Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--color-cyan, #06b6d4)" />
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
            MINE MONITORING MAP
          </h2>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.68rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--text-muted, #64748b)',
            background: 'rgba(0,0,0,0.3)',
            padding: '3px 8px',
            borderRadius: '4px',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
          }}
        >
          <Compass size={11} />
          FICTIONAL MINE SCHEMATIC
        </div>
      </div>

      {/* SVG Map Canvas */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '320px',
          background: 'radial-gradient(ellipse at center, rgba(14,24,40,0.85) 0%, rgba(8,12,20,0.95) 100%)',
          borderRadius: 'var(--radius-md, 8px)',
          border: '1px solid var(--border-light, rgba(255,255,255,0.1))',
          overflow: 'hidden',
        }}
      >
        {/* Background Grid Lines (Fictional Underground Adits & Drifts) */}
        <svg
          viewBox="0 0 440 340"
          style={{ width: '100%', height: '100%' }}
          role="img"
          aria-label="Fictional Mine Gallery Schematic"
        >
          <defs>
            {/* Grid Pattern */}
            <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" />
            </pattern>
            {/* Safe Glow */}
            <filter id="glowSafe" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            {/* Warning Glow */}
            <filter id="glowWarning" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            {/* Danger Glow */}
            <filter id="glowDanger" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Grid Background */}
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Fictional Zone Outlines */}
          {/* Zone Z01 */}
          <path
            d="M 60 50 L 380 50 L 380 150 L 60 150 Z"
            fill="rgba(6, 182, 212, 0.03)"
            stroke="rgba(6, 182, 212, 0.2)"
            strokeWidth="1"
            strokeDasharray="4 3"
          />
          <text x="75" y="72" fill="rgba(6, 182, 212, 0.6)" fontSize="10" fontFamily="monospace" fontWeight="600">
            ZONE Z01 • UPPER SEAM (140-160m)
          </text>

          {/* Zone Z02 */}
          <path
            d="M 60 165 L 380 165 L 380 250 L 60 250 Z"
            fill="rgba(245, 158, 11, 0.03)"
            stroke="rgba(245, 158, 11, 0.2)"
            strokeWidth="1"
            strokeDasharray="4 3"
          />
          <text x="75" y="185" fill="rgba(245, 158, 11, 0.6)" fontSize="10" fontFamily="monospace" fontWeight="600">
            ZONE Z02 • MAIN HAULAGE & PILLAR (190-235m)
          </text>

          {/* Zone Z03 */}
          <path
            d="M 60 260 L 380 260 L 380 325 L 60 325 Z"
            fill="rgba(168, 85, 247, 0.03)"
            stroke="rgba(168, 85, 247, 0.2)"
            strokeWidth="1"
            strokeDasharray="4 3"
          />
          <text x="75" y="278" fill="rgba(168, 85, 247, 0.6)" fontSize="10" fontFamily="monospace" fontWeight="600">
            ZONE Z03 • EXTRACTION FACE (250m)
          </text>

          {/* Underground Drift Tunnels (Connecting Galleries) */}
          <path
            d="M 130 110 L 270 115 L 260 215 L 210 285 L 330 270"
            fill="none"
            stroke="rgba(255, 255, 255, 0.12)"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <path
            d="M 130 110 L 120 220 L 210 285"
            fill="none"
            stroke="rgba(255, 255, 255, 0.12)"
            strokeWidth="3"
            strokeLinecap="round"
          />

          {/* Stress Contour Anomaly Ring around Warning Nodes N03 and N05 */}
          <ellipse
            cx="210"
            cy="285"
            rx="45"
            ry="28"
            fill="rgba(245, 158, 11, 0.08)"
            stroke="rgba(245, 158, 11, 0.35)"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />

          {/* Render Nodes */}
          {nodeList.map((node) => {
            const isSelected = node.node_id === selectedNodeId;
            const config = getStatusConfig(node.status);
            const { x, y } = node.position;

            return (
              <g
                key={node.node_id}
                onClick={() => onSelectNode(node.node_id)}
                style={{ cursor: 'pointer' }}
                tabIndex={0}
                role="button"
                aria-label={`Node ${node.node_id}, Status ${node.status}, Risk ${node.risk_score}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectNode(node.node_id);
                  }
                }}
              >
                {/* Generous Click Hit Area */}
                <circle
                  cx={x}
                  cy={y}
                  r="24"
                  fill="transparent"
                />

                {/* Selection Highlight Ring */}
                {isSelected && (
                  <circle
                    cx={x}
                    cy={y}
                    r="18"
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="1.5"
                    strokeDasharray="2 2"
                    opacity="0.9"
                  />
                )}

                {/* Status Glow Ring */}
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? "13" : "10"}
                  fill={config.color}
                  opacity={node.status === 'WARNING' || node.status === 'DANGER' ? '0.35' : '0.2'}
                  filter={
                    node.status === 'DANGER'
                      ? 'url(#glowDanger)'
                      : node.status === 'WARNING'
                      ? 'url(#glowWarning)'
                      : 'url(#glowSafe)'
                  }
                />

                {/* Main Node Dot */}
                <circle
                  cx={x}
                  cy={y}
                  r="7"
                  fill={config.color}
                  stroke="#ffffff"
                  strokeWidth={isSelected ? '2' : '1'}
                />

                {/* Node ID Tag */}
                <text
                  x={x + 12}
                  y={y - 5}
                  fill="#ffffff"
                  fontSize="10"
                  fontFamily="var(--font-mono, monospace)"
                  fontWeight="700"
                >
                  {node.node_id}
                </text>

                {/* Risk Score Pill */}
                <text
                  x={x + 12}
                  y={y + 8}
                  fill={config.textColor}
                  fontSize="8.5"
                  fontFamily="var(--font-mono, monospace)"
                  fontWeight="600"
                >
                  R:{node.risk_score}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Fictional Coordinates Disclaimer Banner at bottom */}
        <div
          style={{
            position: 'absolute',
            bottom: '6px',
            left: '10px',
            right: '10px',
            fontSize: '0.62rem',
            color: 'rgba(255, 255, 255, 0.4)',
            fontFamily: 'var(--font-mono, monospace)',
            pointerEvents: 'none',
          }}
        >
          * Fictional coordinate grid for industrial demonstration purposes
        </div>
      </div>

      {/* Selected Node Information Panel */}
      {selectedNode && (
        <div
          style={{
            marginTop: '12px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm, 6px)',
            backgroundColor: 'rgba(0, 0, 0, 0.35)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MapPin size={14} color="var(--color-cyan, #06b6d4)" />
              <span
                style={{
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono, monospace)',
                  color: '#ffffff',
                }}
              >
                Node {selectedNode.node_id}
              </span>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary, #94a3b8)', fontFamily: 'var(--font-mono, monospace)' }}>
              Zone: <strong style={{ color: '#ffffff' }}>{selectedNode.zone_id}</strong>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary, #94a3b8)', fontFamily: 'var(--font-mono, monospace)' }}>
              Status: <NodeStatus status={selectedNode.status} size="sm" />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono, monospace)' }}>
              Risk: <strong style={{ color: selectedNode.risk_score > 50 ? 'var(--color-warning, #f59e0b)' : 'var(--color-safe, #10b981)' }}>{selectedNode.risk_score}</strong>
            </div>

            <div style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono, monospace)' }}>
              Trend: <strong style={{ color: selectedNode.trend === 'ESCALATING' ? 'var(--color-warning, #f59e0b)' : '#ffffff' }}>{selectedNode.trend}</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
