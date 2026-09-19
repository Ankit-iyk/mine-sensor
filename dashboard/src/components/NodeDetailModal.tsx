'use client';

import React from 'react';
import { X, Activity, Compass, Cpu, Clock, Network, AlertTriangle, ShieldCheck } from 'lucide-react';
import { LegacyNodeStatus as NodeStatus } from '@/types';

interface NodeDetailModalProps {
  node: NodeStatus | null;
  onClose: () => void;
}

export function NodeDetailModal({ node, onClose }: NodeDetailModalProps) {
  if (!node) return null;

  const getRiskColor = (score: number) => {
    if (score >= 75) return '#f43f5e';
    if (score >= 45) return '#f59e0b';
    return '#10b981';
  };

  const riskColor = getRiskColor(node.latest_risk);

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(5, 8, 15, 0.75)',
        backdropFilter: 'blur(10px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '680px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-xl)',
          padding: '28px',
          boxShadow: '0 20px 50px rgba(0,0,0,0.7), 0 0 30px rgba(6, 182, 212, 0.15)',
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                {node.node_id}
              </h2>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--text-secondary)' }}>
                {node.zone_id}
              </span>
              <span
                className={`badge ${
                  node.state === 'DANGER' ? 'badge-danger' : node.state === 'WARNING' ? 'badge-warning' : 'badge-safe'
                }`}
              >
                {node.state}
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Geotechnical Subsurface Telemetry Probe • Depth: -{node.depth_m}m Below Ground Level
            </p>
          </div>

          <button
            onClick={onClose}
            className="btn-secondary"
            style={{ padding: '6px', borderRadius: '50%' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Risk Banner */}
        <div
          style={{
            background: 'rgba(10, 15, 26, 0.6)',
            border: `1px solid ${node.state === 'DANGER' ? 'var(--color-danger-border)' : 'var(--border-subtle)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '16px 20px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Composite Geotechnical Risk Score
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '2rem', fontWeight: 800, color: riskColor }}>
                {node.latest_risk.toFixed(1)}
              </span>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>/ 100</span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Stability Grade</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-cyan)' }}>
              GRADE {node.stability_grade}
            </div>
          </div>
        </div>

        {/* 2-Column Telemetry & ML Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '20px' }}>
          
          {/* Signal Processing: Kalman Filtered Tilt */}
          <div style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-cyan)' }}>
              <Compass size={16} />
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700 }}>Kalman-Denoised Tilt</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Tilt X Angle:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{node.tilt_x.toFixed(3)}°</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Tilt Y Angle:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{node.tilt_y.toFixed(3)}°</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Angular Velocity:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: node.tilt_rate > 0.03 ? '#f43f5e' : '#10b981' }}>
                  {node.tilt_rate.toFixed(4)}°/s
                </span>
              </div>
            </div>
          </div>

          {/* Vibration & Micro-Seismic */}
          <div style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-electric)' }}>
              <Activity size={16} />
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700 }}>Micro-Seismic Vibration</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>ADC Intensity:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{node.vibration_intensity}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Normalized Power:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {(node.vibration_intensity / 1023).toFixed(3)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Seismic Activity:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: node.vibration_intensity > 200 ? '#f43f5e' : '#10b981' }}>
                  {node.vibration_intensity > 200 ? 'ELEVATED' : 'QUIESCENT'}
                </span>
              </div>
            </div>
          </div>

          {/* Temporal Precursor Stage */}
          <div style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-warning)' }}>
              <Clock size={16} />
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700 }}>Temporal Precursor Stage</h3>
            </div>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '6px' }}>
              {node.precursor_stage}
            </p>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              Evaluates acceleration of creep strain vectors prior to macro-failure.
            </p>
          </div>

          {/* Spatial Neighbors Correlation */}
          <div style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'var(--color-purple)' }}>
              <Network size={16} />
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700 }}>Spatial Neighbor Mesh</h3>
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {['NODE_01', 'NODE_02', 'NODE_03', 'NODE_04'].filter((n) => n !== node.node_id).map((n) => (
                <span
                  key={n}
                  style={{
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    background: 'rgba(168, 85, 247, 0.15)',
                    color: '#e9d5ff',
                    border: '1px solid rgba(168, 85, 247, 0.3)',
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  {n}
                </span>
              ))}
            </div>
          </div>

        </div>

        {/* Footer info */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
          <span>Last telemetry ingestion: {new Date(node.last_updated).toLocaleTimeString()}</span>
          <button onClick={onClose} className="btn-primary" style={{ padding: '6px 14px', fontSize: '0.78rem' }}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
