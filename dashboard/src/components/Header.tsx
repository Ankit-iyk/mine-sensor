'use client';

import React from 'react';
import { Activity, Radio, Database, Server, RefreshCw, AlertTriangle, RadioTower, Zap } from 'lucide-react';
import { SystemStatus } from '@/types/system';

interface HeaderProps {
  systemStatus: SystemStatus;
  currentTime: string;
  isDemoMode: boolean;
  wsStatus?: 'connected' | 'connecting' | 'disconnected';
  onToggleDemoMode?: () => void;
  onRefresh?: () => void;
}

export function Header({
  systemStatus,
  currentTime,
  isDemoMode,
  wsStatus = 'disconnected',
  onToggleDemoMode,
  onRefresh,
}: HeaderProps) {
  const isApiOnline = systemStatus.backend_status === 'ONLINE';
  const isMqttConnected = systemStatus.mqtt_status === 'CONNECTED';
  const isDbHealthy = systemStatus.db_status === 'HEALTHY';

  return (
    <header
      className="glass-panel"
      style={{
        padding: '16px 24px',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
      }}
    >
      {/* Left: Branding & Mode Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div
          style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: isDemoMode
              ? 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)'
              : 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: isDemoMode
              ? '0 0 20px rgba(168, 85, 247, 0.4)'
              : '0 0 20px rgba(6, 182, 212, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            transition: 'all 0.3s ease',
          }}
        >
          <Activity size={22} color="#ffffff" />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1
              style={{
                fontSize: '1.45rem',
                fontWeight: 800,
                letterSpacing: '-0.02em',
                color: '#ffffff',
                margin: 0,
                lineHeight: 1.2,
              }}
            >
              SUBSENSE
            </h1>

            {/* Overall System Status */}
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '3px 10px',
                borderRadius: 'var(--radius-sm, 4px)',
                backgroundColor: isApiOnline ? 'rgba(16, 185, 129, 0.14)' : 'rgba(239, 68, 68, 0.14)',
                border: `1px solid ${isApiOnline ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                color: isApiOnline ? 'var(--color-safe, #10b981)' : '#f87171',
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '0.74rem',
                fontWeight: 700,
                letterSpacing: '0.05em',
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  backgroundColor: isApiOnline ? '#10b981' : '#ef4444',
                  boxShadow: `0 0 8px ${isApiOnline ? '#10b981' : '#ef4444'}`,
                }}
              />
              {isApiOnline ? 'SYSTEM ONLINE' : 'SYSTEM DEGRADED'}
            </span>

            {/* LIVE vs DEMO Mode Pill */}
            {isDemoMode ? (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '3px 9px',
                  borderRadius: 'var(--radius-sm, 4px)',
                  backgroundColor: 'rgba(168, 85, 247, 0.15)',
                  border: '1px solid rgba(168, 85, 247, 0.45)',
                  color: '#c084fc',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                }}
                title="Mock telemetry data is currently active for demonstration"
              >
                <AlertTriangle size={11} />
                DEMO MODE
              </span>
            ) : (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '3px 9px',
                  borderRadius: 'var(--radius-sm, 4px)',
                  backgroundColor: 'rgba(6, 182, 212, 0.15)',
                  border: '1px solid rgba(6, 182, 212, 0.45)',
                  color: '#38bdf8',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                }}
                title="Connected to live FastAPI backend and sensor stream"
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: '#38bdf8',
                    boxShadow: '0 0 6px #38bdf8',
                  }}
                />
                LIVE MODE
              </span>
            )}
          </div>

          <p
            style={{
              fontSize: '0.82rem',
              color: 'var(--text-secondary, #94a3b8)',
              marginTop: '3px',
              fontWeight: 400,
            }}
          >
            Predictive Mine Subsidence Intelligence System
          </p>
        </div>
      </div>

      {/* Right: Subsystem Status Indicators, Mode Toggle & Clock */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        {/* Real-time Clock */}
        <div
          style={{
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '0.85rem',
            fontWeight: 600,
            color: '#ffffff',
            background: 'rgba(0, 0, 0, 0.4)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
            letterSpacing: '0.05em',
          }}
        >
          {currentTime}
        </div>

        {/* API Status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: 'var(--radius-sm, 6px)',
            backgroundColor: isApiOnline ? 'rgba(6, 182, 212, 0.1)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${isApiOnline ? 'rgba(6, 182, 212, 0.3)' : 'rgba(239, 68, 68, 0.4)'}`,
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: isApiOnline ? 'var(--color-cyan, #06b6d4)' : '#f87171',
            fontWeight: 600,
          }}
          title={isApiOnline ? 'FastAPI backend is online' : 'FastAPI backend unreachable'}
        >
          <Server size={12} />
          {isApiOnline ? 'API: ONLINE' : 'API: OFFLINE'}
        </div>

        {/* MQTT Status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: 'var(--radius-sm, 6px)',
            backgroundColor: isMqttConnected ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            border: `1px solid ${isMqttConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: isMqttConnected ? '#34d399' : '#fbbf24',
            fontWeight: 600,
          }}
          title="EMQX / MQTT Broker Telemetry Pipeline"
        >
          <Radio size={12} />
          MQTT: {systemStatus.mqtt_status}
        </div>

        {/* Database Status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: 'var(--radius-sm, 6px)',
            backgroundColor: isDbHealthy ? 'rgba(59, 130, 246, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${isDbHealthy ? 'rgba(59, 130, 246, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: isDbHealthy ? '#60a5fa' : '#f87171',
            fontWeight: 600,
          }}
          title="TimescaleDB Telemetry Storage"
        >
          <Database size={12} />
          DB: {systemStatus.db_status}
        </div>

        {/* WebSocket Live Stream Indicator (in Live Mode) */}
        {!isDemoMode && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              borderRadius: 'var(--radius-sm, 6px)',
              backgroundColor:
                wsStatus === 'connected'
                  ? 'rgba(16, 185, 129, 0.1)'
                  : wsStatus === 'connecting'
                  ? 'rgba(245, 158, 11, 0.1)'
                  : 'rgba(239, 68, 68, 0.12)',
              border: `1px solid ${
                wsStatus === 'connected'
                  ? 'rgba(16, 185, 129, 0.3)'
                  : wsStatus === 'connecting'
                  ? 'rgba(245, 158, 11, 0.3)'
                  : 'rgba(239, 68, 68, 0.3)'
              }`,
              fontSize: '0.74rem',
              fontFamily: 'var(--font-mono, monospace)',
              color:
                wsStatus === 'connected'
                  ? '#34d399'
                  : wsStatus === 'connecting'
                  ? '#fbbf24'
                  : '#f87171',
              fontWeight: 600,
            }}
            title="Real-time /ws/alerts WebSocket stream"
          >
            <RadioTower size={12} />
            {wsStatus === 'connected'
              ? 'WS: CONNECTED'
              : wsStatus === 'connecting'
              ? 'WS: CONNECTING'
              : 'LIVE STREAM DISCONNECTED'}
          </div>
        )}

        {/* Demo / Live Toggle Button */}
        {onToggleDemoMode && (
          <button
            onClick={onToggleDemoMode}
            className="btn-secondary"
            style={{
              padding: '6px 12px',
              fontSize: '0.74rem',
              fontFamily: 'var(--font-mono, monospace)',
              borderColor: isDemoMode ? 'rgba(168, 85, 247, 0.5)' : 'rgba(6, 182, 212, 0.5)',
              color: isDemoMode ? '#e9d5ff' : '#bae6fd',
            }}
            title={isDemoMode ? 'Switch to Live FastAPI Backend' : 'Switch to Demo Mock Data'}
          >
            <Zap size={12} color={isDemoMode ? '#c084fc' : '#38bdf8'} />
            {isDemoMode ? 'SWITCH TO LIVE' : 'SWITCH TO DEMO'}
          </button>
        )}

        {/* Force Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="btn-secondary"
            style={{ padding: '6px 10px' }}
            title="Refresh operational telemetry"
          >
            <RefreshCw size={13} />
          </button>
        )}
      </div>
    </header>
  );
}
