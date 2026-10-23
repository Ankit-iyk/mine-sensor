import type { AlertExplanation, Incident, MineNode, RiskPoint, SystemStatus, SystemHealth } from '@/types';

const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`Backend request failed (${response.status}): ${path}`);
  }
  return await response.json() as T;
}

interface BackendSystemStatus {
  backend: string;
  mqtt: string;
  database: string;
  mode: SystemStatus['mode'];
  last_hardware_seen: string | null;
  last_simulator_seen: string | null;
}

interface TelemetrySummary {
  node_id: string;
  zone_id: string;
  latest_timestamp: string;
  latest_tilt_x: number;
  latest_tilt_y: number;
  latest_vibration: number;
}

interface BackendRisk {
  node_id: string;
  zone_id: string;
  timestamp: string;
  risk_score: number;
  state: string;
  trend: string;
  reasons: string | null;
}

interface BackendAnomaly {
  node_id: string;
  anomaly_score: number;
}

const statusFromRisk = (state?: string): MineNode['status'] => {
  if (state === 'SAFE' || state === 'WARNING' || state === 'DANGER') return state;
  return 'UNKNOWN';
};

const trendFromRisk = (trend?: string): MineNode['trend'] => {
  if (trend === 'ESCALATING' || trend === 'DECREASING' || trend === 'PERSISTENT') return trend;
  return 'STABLE';
};

export async function getSystemHealth(): Promise<{ data: SystemHealth }> {
  const response = await get<SystemHealth>('/api/health');
  return { data: response };
}

export async function getSystemStatus(_demo: boolean): Promise<{ data: SystemStatus }> {
  const status = await get<BackendSystemStatus>('/api/system/status');
  const online = status.backend.toLowerCase() === 'online';
  return {
    data: {
      mode: status.mode,
      last_hardware_seen: status.last_hardware_seen,
      last_simulator_seen: status.last_simulator_seen,
      overall_mine_status: 'UNKNOWN',
      active_nodes: 0,
      total_nodes: 0,
      warning_nodes: 0,
      active_incidents: 0,
      system_health_percent: online ? 100 : 0,
      mqtt_status: status.mqtt.toLowerCase() === 'connected' ? 'CONNECTED' : 'DISCONNECTED',
      backend_status: online ? 'ONLINE' : 'OFFLINE',
      db_status: status.database.toLowerCase() === 'connected' ? 'HEALTHY' : 'OFFLINE',
      is_demo_mode: false,
      last_updated: new Date().toISOString(),
    },
  };
}

export async function getNodes(_demo: boolean): Promise<{ data: MineNode[] }> {
  const [summaries, risks, anomalies] = await Promise.all([
    get<TelemetrySummary[]>('/api/telemetry/summary'),
    get<BackendRisk[]>('/api/risk/latest?limit=500'),
    get<BackendAnomaly[]>('/api/anomalies/latest?limit=500'),
  ]);
  const riskByNode = new Map<string, BackendRisk>();
  for (const risk of risks) {
    if (!riskByNode.has(risk.node_id)) riskByNode.set(risk.node_id, risk);
  }
  const anomalyByNode = new Map<string, BackendAnomaly>();
  for (const anomaly of anomalies) {
    if (!anomalyByNode.has(anomaly.node_id)) anomalyByNode.set(anomaly.node_id, anomaly);
  }
  return {
    data: summaries.map((summary, index) => {
      const risk = riskByNode.get(summary.node_id);
      return {
        node_id: summary.node_id,
        zone_id: summary.zone_id,
        status: statusFromRisk(risk?.state),
        risk_score: risk?.risk_score ?? 0,
        trend: trendFromRisk(risk?.trend),
        position: { x: 12 + (index % 4) * 25, y: 20 + Math.floor(index / 4) * 50 },
        tilt_x: summary.latest_tilt_x,
        tilt_y: summary.latest_tilt_y,
        vibration: summary.latest_vibration,
        anomaly_score: anomalyByNode.get(summary.node_id)?.anomaly_score ?? 0,
        last_updated: summary.latest_timestamp,
      };
    }),
  };
}

export async function getRisks(nodeId: string, _demo: boolean): Promise<{ data: RiskPoint[] }> {
  const risks = await get<BackendRisk[]>(
    `/api/risk/latest?limit=500&node_id=${encodeURIComponent(nodeId)}`,
  );
  return {
    data: [...risks].reverse().map((risk) => ({
      timestamp: risk.timestamp,
      risk_score: risk.risk_score,
      status: statusFromRisk(risk.state),
    })),
  };
}

export async function getIncidents(_demo: boolean): Promise<{ data: Incident[] }> {
  return { data: await get<Incident[]>('/api/incidents') };
}

export async function getAlertExplanation(
  nodeId: string,
  _demo: boolean,
): Promise<{ data: AlertExplanation }> {
  const risks = await get<BackendRisk[]>(
    `/api/risk/latest?limit=1&node_id=${encodeURIComponent(nodeId)}`,
  );
  const risk = risks[0];
  let reasons: string[] = [];
  if (risk?.reasons) {
    try {
      const parsed: unknown = JSON.parse(risk.reasons);
      if (Array.isArray(parsed) && parsed.every((reason) => typeof reason === 'string')) {
        reasons = parsed;
      }
    } catch (error) {
      console.error('Could not parse backend risk explanation', error);
      reasons = [risk.reasons];
    }
  }
  return {
    data: {
      node_id: nodeId,
      zone_id: risk?.zone_id,
      risk_score: risk?.risk_score ?? 0,
      trend: risk?.trend ?? 'UNKNOWN',
      status: risk?.state ?? 'UNKNOWN',
      title: risk ? 'Latest backend risk assessment' : 'No risk assessment available',
      reasons,
    },
  };
}
