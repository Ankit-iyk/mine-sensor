import type { AlertExplanation, Incident, MineNode, RiskPoint, SystemStatus } from '@/types';

const makeTrajectory = (score: number): RiskPoint[] =>
  Array.from({ length: 12 }, (_, index) => ({
    timestamp: `10:${String(20 + index).padStart(2, '0')}`,
    risk_score: Math.max(0, score - (11 - index) * 2),
    status: score >= 60 ? 'WARNING' : 'SAFE',
  }));

export const DEMO_NODES: Record<string, MineNode> = Object.fromEntries(
  ['N01', 'N02', 'N03', 'N04', 'N05', 'N06'].map((node_id, index) => {
    const risk_score = [18, 24, 31, 22, 45, 16][index];
    const node: MineNode = {
      node_id,
      zone_id: `ZONE-${String.fromCharCode(65 + Math.floor(index / 2))}`,
      status: risk_score >= 60 ? 'WARNING' : 'SAFE',
      risk_score,
      trend: index === 4 ? 'ESCALATING' : 'STABLE',
      position: { x: 18 + (index % 3) * 30, y: 24 + Math.floor(index / 3) * 42, depth_m: 100 + index * 10 },
      tilt_x: 0.7 + index * 0.1,
      tilt_y: 0.5 + index * 0.08,
      vibration: index === 4 ? 24 : 4,
      anomaly_score: index === 4 ? 0.42 : 0.08,
      last_updated: '10:32:41',
    };
    return [node_id, node];
  }),
);

export const DEMO_RISK_TRAJECTORIES: Record<string, RiskPoint[]> = Object.fromEntries(
  Object.values(DEMO_NODES).map((node) => [node.node_id, makeTrajectory(node.risk_score)]),
);

export const DEMO_SYSTEM_STATUS: SystemStatus = {
  mode: 'OFFLINE',
  last_hardware_seen: null,
  last_simulator_seen: null,
  overall_mine_status: 'WARNING',
  active_nodes: 6,
  total_nodes: 6,
  warning_nodes: 1,
  active_incidents: 1,
  system_health_percent: 100,
  mqtt_status: 'CONNECTED',
  backend_status: 'ONLINE',
  db_status: 'HEALTHY',
  is_demo_mode: true,
  last_updated: '10:32:41',
};

export const DEMO_INCIDENTS: Incident[] = [{
  id: 'DEMO-1',
  node_id: 'N05',
  zone_id: 'ZONE-C',
  severity: 'WARNING',
  status: 'ACTIVE',
  risk_score: 45,
  trend: 'ESCALATING',
  created_at: '10:30:00',
  reason: 'Gradual tilt trend detected in demonstration data.',
}];

export const DEMO_EXPLANATIONS: Record<string, AlertExplanation> = Object.fromEntries(
  Object.values(DEMO_NODES).map((node) => [
    node.node_id,
    {
      node_id: node.node_id,
      zone_id: node.zone_id,
      risk_score: node.risk_score,
      trend: node.trend,
      status: node.status,
      title: node.node_id === 'N05' ? 'Gradual tilt trend' : 'Stable sensor readings',
      reasons: node.node_id === 'N05' ? ['Demonstration data indicates a gradual tilt trend.'] : ['No elevated indicators in demonstration data.'],
      metrics_summary: { tilt_deviation: 'Demo data', vibration_level: 'Demo data' },
    },
  ]),
);

export const DEFAULT_EXPLANATION = DEMO_EXPLANATIONS.N05;
