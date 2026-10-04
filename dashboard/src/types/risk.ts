import { NodeStatus } from './node';

export interface RiskPoint {
  timestamp: string;
  risk_score: number;
  status?: NodeStatus;
}

export interface Risk {
  node_id: string;
  current_risk: number;
  trend: 'STABLE' | 'ESCALATING' | 'DECREASING' | 'UNKNOWN';
  trajectory: RiskPoint[];
  state?: NodeStatus;
}
