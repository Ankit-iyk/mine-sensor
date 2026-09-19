'use client';

import React from 'react';
import { useDashboardData } from '@/hooks/useDashboardData';
import { Header } from '@/components/Header';
import { SummaryCards } from '@/components/SummaryCards';
import { MineMap } from '@/components/MineMap';
import { RiskTrajectoryChart } from '@/components/RiskTrajectoryChart';
import { LiveSensorPanel } from '@/components/LiveSensorPanel';
import { ActiveIncidents } from '@/components/ActiveIncidents';
import { AlertExplanation } from '@/components/AlertExplanation';

export default function DashboardPage() {
  const {
    systemStatus,
    isDemoMode,
    currentTime,
    nodes,
    selectedNodeId,
    selectedNode,
    setSelectedNodeId,
    selectedTelemetry,
    riskTrajectory,
    currentRisk,
    riskTrend,
    incidents,
    explanation,
    wsStatus,
    refreshData,
    toggleDemoMode,
  } = useDashboardData();

  return (
    <main
      style={{
        maxWidth: '1680px',
        margin: '0 auto',
        padding: '24px 20px',
        position: 'relative',
        zIndex: 1,
      }}
    >
      {/* 1. Header with System Status, Subsystem Health & Live Clock */}
      <Header
        systemStatus={systemStatus}
        currentTime={currentTime}
        isDemoMode={isDemoMode}
        wsStatus={wsStatus}
        onToggleDemoMode={toggleDemoMode}
        onRefresh={refreshData}
      />

      {/* 2. Overview Summary Cards (Mine Status, Active Nodes, Warnings, Incidents, System Health) */}
      <SummaryCards systemStatus={systemStatus} />

      {/* 3. Middle Section: Mine Monitoring Map (Left) + Risk Trajectory (Right) */}
      <section
        aria-label="Spatial-Temporal Risk Twin"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
          gap: '20px',
          marginBottom: '20px',
        }}
      >
        <MineMap
          nodes={nodes}
          selectedNodeId={selectedNodeId}
          onSelectNode={(nodeId) => setSelectedNodeId(nodeId)}
        />

        <RiskTrajectoryChart
          nodeId={selectedNodeId}
          currentRisk={currentRisk}
          trend={riskTrend}
          trajectory={riskTrajectory}
        />
      </section>

      {/* 4. Lower Section: Live Sensor Data (Left) + Active Incidents (Right) */}
      <section
        aria-label="Live Telemetry and Incident Management"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
          gap: '20px',
          marginBottom: '20px',
        }}
      >
        <LiveSensorPanel
          telemetry={selectedTelemetry}
          riskScore={currentRisk}
          trend={riskTrend}
          status={selectedNode.status}
        />

        <ActiveIncidents
          incidents={incidents}
          selectedNodeId={selectedNodeId}
          onSelectNode={(nodeId) => setSelectedNodeId(nodeId)}
        />
      </section>

      {/* 5. Bottom Section: Explainable AI / Alert Diagnostics */}
      <AlertExplanation explanation={explanation} />
    </main>
  );
}
