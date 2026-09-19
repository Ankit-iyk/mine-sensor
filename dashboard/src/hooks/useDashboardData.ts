'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  MineNode,
  Telemetry,
  RiskPoint,
  Incident,
  SystemStatus,
  AlertExplanation,
  NodeStatus,
} from '@/types';
import {
  DEMO_SYSTEM_STATUS,
  DEMO_NODES,
  DEMO_RISK_TRAJECTORIES,
  DEMO_INCIDENTS,
  DEMO_EXPLANATIONS,
  DEFAULT_EXPLANATION,
} from '@/lib/mock-data';
import {
  getSystemStatus,
  getNodes,
  getRisks,
  getIncidents,
  getAlertExplanation,
  getSystemHealth,
} from '@/lib/api';
import { SubsenseWebSocketClient, SubsenseStreamEvent, BackendAlertEvent } from '@/lib/websocket';

export interface UseDashboardDataReturn {
  // System Status & Connection State
  systemStatus: SystemStatus;
  isDemoMode: boolean;
  currentTime: string;
  wsStatus: 'connected' | 'connecting' | 'disconnected';
  isLiveConnected: boolean;

  // Nodes & Selection
  nodes: Record<string, MineNode>;
  nodeList: MineNode[];
  selectedNodeId: string;
  selectedNode: MineNode;
  setSelectedNodeId: (id: string) => void;

  // Selected Node Telemetry
  selectedTelemetry: Telemetry;

  // Risk Trajectory
  riskTrajectory: RiskPoint[];
  currentRisk: number;
  riskTrend: 'STABLE' | 'ESCALATING' | 'DECREASING' | 'PERSISTENT' | 'UNKNOWN';

  // Incidents & Explanations
  incidents: Incident[];
  explanation: AlertExplanation;

  // Control Actions
  refreshData: () => Promise<void>;
  toggleDemoMode: () => void;
}

export function useDashboardData(): UseDashboardDataReturn {
  // Default to Live Mode unless NEXT_PUBLIC_DEMO_MODE === 'true'
  const initialDemo = process.env.NEXT_PUBLIC_DEMO_MODE === 'true';
  const [isDemoMode, setIsDemoMode] = useState<boolean>(initialDemo);

  const [systemStatus, setSystemStatus] = useState<SystemStatus>(() => ({
    ...DEMO_SYSTEM_STATUS,
    is_demo_mode: initialDemo,
  }));
  const [nodes, setNodes] = useState<Record<string, MineNode>>(DEMO_NODES);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('N05');
  const [incidents, setIncidents] = useState<Incident[]>(initialDemo ? DEMO_INCIDENTS : []);
  const [riskTrajectory, setRiskTrajectory] = useState<RiskPoint[]>(DEMO_RISK_TRAJECTORIES.N05);
  const [explanation, setExplanation] = useState<AlertExplanation>(DEMO_EXPLANATIONS.N05);
  const [currentTime, setCurrentTime] = useState<string>('10:32:41');
  const [wsStatus, setWsStatus] = useState<'connected' | 'connecting' | 'disconnected'>('disconnected');

  const wsClientRef = useRef<SubsenseWebSocketClient | null>(null);

  // 1. Real-time clock update (formatted as HH:MM:SS)
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      setCurrentTime(`${hours}:${minutes}:${seconds}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // 2. Fetch / Sync Data
  const refreshData = useCallback(async () => {
    if (isDemoMode) {
      setSystemStatus({
        ...DEMO_SYSTEM_STATUS,
        last_updated: currentTime,
        is_demo_mode: true,
      });
      setNodes(DEMO_NODES);
      setIncidents(DEMO_INCIDENTS);
      setRiskTrajectory(DEMO_RISK_TRAJECTORIES[selectedNodeId] || DEMO_RISK_TRAJECTORIES.N05);
      setExplanation(DEMO_EXPLANATIONS[selectedNodeId] || DEFAULT_EXPLANATION);
      return;
    }

    try {
      const [sysRes, nodesRes, incRes, riskRes, expRes] = await Promise.all([
        getSystemStatus(false),
        getNodes(false),
        getIncidents(false),
        getRisks(selectedNodeId, false),
        getAlertExplanation(selectedNodeId, false),
      ]);

      setSystemStatus(sysRes.data);

      if (nodesRes.data && nodesRes.data.length > 0) {
        const nodeMap: Record<string, MineNode> = {};
        nodesRes.data.forEach((n) => {
          nodeMap[n.node_id] = n;
        });
        setNodes(nodeMap);
      }

      setIncidents(incRes.data);
      if (riskRes.data && riskRes.data.length > 0) {
        setRiskTrajectory(riskRes.data);
      }
      setExplanation(expRes.data);
    } catch {
      // Keep existing data on transient network error
    }
  }, [isDemoMode, selectedNodeId, currentTime]);

  // Initial fetch and periodic polling (every 3.5 seconds) in Live Mode
  useEffect(() => {
    refreshData();
    if (!isDemoMode) {
      const pollTimer = setInterval(refreshData, 3500);
      return () => clearInterval(pollTimer);
    }
  }, [refreshData, isDemoMode]);

  // 3. WebSocket Real-Time Connection
  useEffect(() => {
    if (isDemoMode) {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
      setWsStatus('disconnected');
      return;
    }

    const client = new SubsenseWebSocketClient();
    wsClientRef.current = client;

    const unsubStatus = client.onStatusChange((status) => {
      setWsStatus(status);
    });

    const unsubEvents = client.subscribe((event: SubsenseStreamEvent) => {
      // Check if event is an AlertEvent from AlertEngine
      if ('event_id' in event || ('severity' in event && 'risk_score' in event)) {
        const alert = event as BackendAlertEvent;
        const targetNodeId = alert.node_id;

        // 1. Incrementally update node status in nodes map
        setNodes((prev) => {
          const existing = prev[targetNodeId];
          if (!existing) return prev;
          return {
            ...prev,
            [targetNodeId]: {
              ...existing,
              status: (alert.state as NodeStatus) || existing.status,
              risk_score: Math.round(alert.risk_score),
              trend: alert.risk_score > 60 ? 'ESCALATING' : existing.trend,
              last_updated: alert.timestamp ? alert.timestamp.split('T')[1]?.substring(0, 8) || 'NOW' : 'NOW',
            },
          };
        });

        // 2. Incrementally add to incidents list
        setIncidents((prev) => {
          const alreadyExists = prev.some((i) => i.node_id === targetNodeId && i.status === 'ACTIVE');
          if (alreadyExists) return prev;
          const newIncident: Incident = {
            id: alert.event_id || `INC-${Date.now()}`,
            node_id: alert.node_id,
            zone_id: alert.zone_id,
            severity: (alert.severity?.toUpperCase() as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'WARNING') || 'WARNING',
            status: 'ACTIVE',
            risk_score: Math.round(alert.risk_score),
            trend: alert.risk_score > 60 ? 'ESCALATING' : 'PERSISTENT',
            created_at: alert.timestamp ? alert.timestamp.split('T')[1]?.substring(0, 8) || 'NOW' : 'NOW',
            reason: alert.reason || 'Geotechnical anomaly detected',
            affected_nodes: alert.affected_nodes,
          };
          return [newIncident, ...prev];
        });

        // 3. If the event is for the currently selected node, update current risk & trajectory
        if (targetNodeId === selectedNodeId) {
          setRiskTrajectory((prev) => [
            ...prev.slice(-14),
            {
              timestamp: alert.timestamp ? alert.timestamp.split('T')[1]?.substring(0, 8) || 'NOW' : 'NOW',
              risk_score: Math.round(alert.risk_score),
              status: alert.state as NodeStatus,
            },
          ]);

          if (alert.reason) {
            setExplanation((prev) => ({
              ...prev,
              risk_score: Math.round(alert.risk_score),
              status: alert.state,
              trend: 'ESCALATING',
              reasons: [alert.reason, ...prev.reasons.slice(0, 3)],
            }));
          }
        }
      } else if (event.event === 'risk_update') {
        const targetNodeId = event.node_id;
        setNodes((prev) => {
          const existing = prev[targetNodeId];
          if (!existing) return prev;
          return {
            ...prev,
            [targetNodeId]: {
              ...existing,
              status: (event.state as NodeStatus) || existing.status,
              risk_score: Math.round(event.risk_score),
              trend: event.trend || existing.trend,
            },
          };
        });
      }
    });

    client.connect();

    return () => {
      unsubStatus();
      unsubEvents();
      client.disconnect();
    };
  }, [isDemoMode, selectedNodeId]);

  const toggleDemoMode = useCallback(() => {
    setIsDemoMode((prev) => !prev);
  }, []);

  // Current selected node
  const selectedNode = useMemo(() => {
    return nodes[selectedNodeId] || DEMO_NODES[selectedNodeId] || DEMO_NODES.N05;
  }, [nodes, selectedNodeId]);

  // Selected node telemetry
  const selectedTelemetry: Telemetry = useMemo(() => {
    return {
      node_id: selectedNode.node_id,
      zone_id: selectedNode.zone_id,
      timestamp: selectedNode.last_updated || currentTime,
      tilt_x: selectedNode.tilt_x,
      tilt_y: selectedNode.tilt_y,
      tilt_magnitude: Number(Math.hypot(selectedNode.tilt_x, selectedNode.tilt_y).toFixed(2)),
      vibration: selectedNode.vibration,
      anomaly: selectedNode.anomaly_score,
      accel_x: 0.02,
      accel_y: 0.04,
      accel_z: 9.78,
    };
  }, [selectedNode, currentTime]);

  const currentRisk = selectedNode.risk_score;
  const riskTrend = selectedNode.trend;
  const nodeList = useMemo(() => Object.values(nodes), [nodes]);
  const isLiveConnected = systemStatus.backend_status === 'ONLINE';

  return {
    systemStatus,
    isDemoMode,
    currentTime,
    wsStatus,
    isLiveConnected,
    nodes,
    nodeList,
    selectedNodeId,
    selectedNode,
    setSelectedNodeId,
    selectedTelemetry,
    riskTrajectory,
    currentRisk,
    riskTrend,
    incidents,
    explanation,
    refreshData,
    toggleDemoMode,
  };
}
