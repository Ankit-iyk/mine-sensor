'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { AlertEvent, Incident, LegacyNodeStatus as NodeStatus, SystemHealth, RiskAssessment, AlertSeverity } from '@/types';

const BACKEND_HTTP = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BACKEND_WS = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/alerts';

const INITIAL_NODES: Record<string, NodeStatus> = {
  'NODE_01': {
    node_id: 'NODE_01',
    zone_id: 'ZONE_A',
    x: 22,
    y: 35,
    depth_m: 120,
    latest_risk: 18.5,
    state: 'SAFE',
    trend: 'STABLE',
    tilt_x: 0.12,
    tilt_y: 0.08,
    tilt_rate: 0.002,
    vibration_intensity: 12,
    stability_grade: 'A',
    precursor_stage: 'STAGE_0_QUIESCENT',
    last_updated: new Date().toISOString(),
  },
  'NODE_02': {
    node_id: 'NODE_02',
    zone_id: 'ZONE_A',
    x: 38,
    y: 42,
    depth_m: 145,
    latest_risk: 24.0,
    state: 'SAFE',
    trend: 'STABLE',
    tilt_x: 0.25,
    tilt_y: 0.19,
    tilt_rate: 0.005,
    vibration_intensity: 18,
    stability_grade: 'A',
    precursor_stage: 'STAGE_0_QUIESCENT',
    last_updated: new Date().toISOString(),
  },
  'NODE_03': {
    node_id: 'NODE_03',
    zone_id: 'ZONE_B',
    x: 55,
    y: 58,
    depth_m: 210,
    latest_risk: 72.4,
    state: 'WARNING',
    trend: 'INCREASING',
    tilt_x: 1.65,
    tilt_y: 1.28,
    tilt_rate: 0.048,
    vibration_intensity: 145,
    stability_grade: 'C',
    precursor_stage: 'STAGE_2_PERSISTENT_MICRO_CREEP',
    last_updated: new Date().toISOString(),
  },
  'NODE_04': {
    node_id: 'NODE_04',
    zone_id: 'ZONE_B',
    x: 68,
    y: 65,
    depth_m: 235,
    latest_risk: 84.8,
    state: 'DANGER',
    trend: 'INCREASING',
    tilt_x: 2.45,
    tilt_y: 2.10,
    tilt_rate: 0.082,
    vibration_intensity: 310,
    stability_grade: 'D',
    precursor_stage: 'STAGE_3_ACCELERATING_SUBSIDENCE',
    last_updated: new Date().toISOString(),
  },
  'NODE_05': {
    node_id: 'NODE_05',
    zone_id: 'ZONE_C',
    x: 75,
    y: 82,
    depth_m: 310,
    latest_risk: 32.0,
    state: 'SAFE',
    trend: 'DECREASING',
    tilt_x: 0.38,
    tilt_y: 0.22,
    tilt_rate: -0.004,
    vibration_intensity: 28,
    stability_grade: 'B',
    precursor_stage: 'STAGE_1_EPISODIC_DRIFT',
    last_updated: new Date().toISOString(),
  },
  'NODE_06': {
    node_id: 'NODE_06',
    zone_id: 'ZONE_C',
    x: 88,
    y: 88,
    depth_m: 345,
    latest_risk: 15.2,
    state: 'SAFE',
    trend: 'STABLE',
    tilt_x: 0.05,
    tilt_y: 0.02,
    tilt_rate: 0.001,
    vibration_intensity: 9,
    stability_grade: 'A',
    precursor_stage: 'STAGE_0_QUIESCENT',
    last_updated: new Date().toISOString(),
  },
};

const SAMPLE_INCIDENTS: Incident[] = [
  {
    id: 101,
    node_id: 'NODE_04',
    zone_id: 'ZONE_B',
    created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    severity: 'CRITICAL',
    risk_score: 84.8,
    reason: 'Spatial correlation anomaly: Multi-node shear precursor with accelerating tilt rate > 0.08°/s',
    status: 'ACTIVE',
    resolved_at: null,
    affected_nodes: '["NODE_03", "NODE_04"]',
  },
  {
    id: 102,
    node_id: 'NODE_03',
    zone_id: 'ZONE_B',
    created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    severity: 'HIGH',
    risk_score: 72.4,
    reason: 'Debounced warning triggered: 3 consecutive readings above threshold (tilt drift sustained)',
    status: 'ACTIVE',
    resolved_at: null,
    affected_nodes: '["NODE_03"]',
  },
  {
    id: 99,
    node_id: 'NODE_05',
    zone_id: 'ZONE_C',
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    severity: 'MEDIUM',
    risk_score: 54.0,
    reason: 'Transient drilling vibration anomaly settled back to baseline',
    status: 'RESOLVED',
    resolved_at: new Date(Date.now() - 1000 * 60 * 85).toISOString(),
    affected_nodes: '["NODE_05"]',
  },
];

export function useSubsenseStream() {
  const [nodes, setNodes] = useState<Record<string, NodeStatus>>(INITIAL_NODES);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>(SAMPLE_INCIDENTS);
  const [wsStatus, setWsStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting');
  const [health, setHealth] = useState<SystemHealth>({ status: 'online', mqtt_connected: true, db_connected: true });
  const [simulationMode, setSimulationMode] = useState<boolean>(false);
  const [activeAlertCount, setActiveAlertCount] = useState<number>(2);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch REST data
  const fetchData = useCallback(async () => {
    try {
      // 1. Health
      const healthRes = await fetch(`${BACKEND_HTTP}/api/health`, { cache: 'no-store' });
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth({
          status: healthData.status === 'ok' ? 'online' : 'degraded',
          version: healthData.version,
          mqtt_connected: healthData.mqtt_connected,
          db_connected: healthData.db_connected,
        });
      } else {
        setHealth({ status: 'degraded' });
      }

      // 2. Latest Risk
      const riskRes = await fetch(`${BACKEND_HTTP}/api/risk/latest?limit=50`, { cache: 'no-store' });
      if (riskRes.ok) {
        const riskRows: RiskAssessment[] = await riskRes.json();
        if (riskRows.length > 0) {
          setNodes((prev) => {
            const next = { ...prev };
            riskRows.forEach((r) => {
              if (next[r.node_id]) {
                next[r.node_id] = {
                  ...next[r.node_id],
                  latest_risk: r.risk_score,
                  state: r.state,
                  trend: r.trend,
                  last_updated: r.timestamp,
                };
              }
            });
            return next;
          });
        }
      }

      // 3. Incidents
      const incRes = await fetch(`${BACKEND_HTTP}/api/incidents?limit=50`, { cache: 'no-store' });
      if (incRes.ok) {
        const incRows: Incident[] = await incRes.json();
        if (incRows.length > 0) {
          setIncidents(incRows);
        }
      }
    } catch {
      // Backend may be offline during dev
      setHealth((h) => ({ ...h, status: 'offline' }));
    }
  }, []);

  // WebSocket Connection
  useEffect(() => {
    let isSubscribed = true;

    function connect() {
      if (!isSubscribed) return;
      setWsStatus('connecting');

      try {
        const ws = new WebSocket(BACKEND_WS);
        socketRef.current = ws;

        ws.onopen = () => {
          if (!isSubscribed) return;
          setWsStatus('connected');
        };

        ws.onmessage = (event) => {
          if (!isSubscribed) return;
          try {
            const data: AlertEvent = JSON.parse(event.data);
            if (data.event_id) {
              setAlerts((prev) => [data, ...prev].slice(0, 100));

              // Update node state from alert
              setNodes((prev) => {
                const target = prev[data.node_id];
                if (!target) return prev;
                return {
                  ...prev,
                  [data.node_id]: {
                    ...target,
                    latest_risk: data.risk_score,
                    state: data.state,
                    last_updated: data.timestamp,
                  },
                };
              });

              // Re-fetch incidents on alert
              fetchData();
            }
          } catch (err) {
            console.warn('Failed to parse WS alert:', err);
          }
        };

        ws.onerror = () => {
          if (!isSubscribed) return;
          setWsStatus('disconnected');
        };

        ws.onclose = () => {
          if (!isSubscribed) return;
          setWsStatus('disconnected');
          // Reconnect with backoff
          reconnectTimeoutRef.current = setTimeout(connect, 4000);
        };
      } catch {
        setWsStatus('disconnected');
        reconnectTimeoutRef.current = setTimeout(connect, 5000);
      }
    }

    connect();
    fetchData();
    const interval = setInterval(fetchData, 6000);

    return () => {
      isSubscribed = false;
      if (socketRef.current) socketRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      clearInterval(interval);
    };
  }, [fetchData]);

  // Recalculate active incidents count
  useEffect(() => {
    const active = incidents.filter((i) => i.status === 'ACTIVE').length;
    setActiveAlertCount(active);
  }, [incidents]);

  // Simulated Live Telemetry Generator (when simulation mode is active or triggered)
  useEffect(() => {
    if (!simulationMode) return;

    const simTimer = setInterval(() => {
      setNodes((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((k) => {
          const node = next[k];
          const jitter = (Math.random() - 0.48) * 1.5;
          const newRisk = Math.min(100, Math.max(5, node.latest_risk + jitter));
          const state = newRisk >= 75 ? 'DANGER' : newRisk >= 45 ? 'WARNING' : 'SAFE';
          const trend = jitter > 0.3 ? 'INCREASING' : jitter < -0.3 ? 'DECREASING' : 'STABLE';

          next[k] = {
            ...node,
            latest_risk: Math.round(newRisk * 10) / 10,
            state,
            trend,
            tilt_rate: Math.round((node.tilt_rate + (Math.random() - 0.5) * 0.005) * 1000) / 1000,
            vibration_intensity: Math.max(5, Math.round(node.vibration_intensity + (Math.random() - 0.5) * 20)),
            last_updated: new Date().toISOString(),
          };
        });
        return next;
      });

      // Random alert injection occasionally
      if (Math.random() > 0.7) {
        const targetNode = Math.random() > 0.5 ? 'NODE_04' : 'NODE_03';
        const severities: AlertSeverity[] = ['HIGH', 'CRITICAL', 'MEDIUM'];
        const sev = severities[Math.floor(Math.random() * severities.length)];
        const newAlert: AlertEvent = {
          event_id: `evt-sim-${Date.now().toString().slice(-5)}`,
          node_id: targetNode,
          zone_id: 'ZONE_B',
          timestamp: new Date().toISOString(),
          severity: sev,
          risk_score: Math.round(75 + Math.random() * 20),
          state: sev === 'CRITICAL' ? 'DANGER' : 'WARNING',
          reason: `Simulated precursor burst: shear strain gradient exceeded safe threshold on ${targetNode}`,
          affected_nodes: [targetNode, targetNode === 'NODE_04' ? 'NODE_03' : 'NODE_02'],
        };
        setAlerts((prev) => [newAlert, ...prev].slice(0, 100));
      }
    }, 2500);

    return () => clearInterval(simTimer);
  }, [simulationMode]);

  // Action: Resolve Incident
  const resolveIncident = async (id: number) => {
    try {
      const res = await fetch(`${BACKEND_HTTP}/api/incidents/${id}/resolve`, {
        method: 'POST',
      });
      if (res.ok) {
        setIncidents((prev) =>
          prev.map((inc) =>
            inc.id === id
              ? { ...inc, status: 'RESOLVED', resolved_at: new Date().toISOString() }
              : inc
          )
        );
        return true;
      }
    } catch {
      // Optimistic fallback for testing
      setIncidents((prev) =>
        prev.map((inc) =>
          inc.id === id
            ? { ...inc, status: 'RESOLVED', resolved_at: new Date().toISOString() }
            : inc
        )
      );
      return true;
    }
    return false;
  };

  return {
    nodes,
    alerts,
    incidents,
    wsStatus,
    health,
    simulationMode,
    setSimulationMode,
    activeAlertCount,
    resolveIncident,
    refreshData: fetchData,
  };
}
