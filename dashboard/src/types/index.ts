export * from './node';
export * from './telemetry';
export * from './risk';
export * from './incident';
export * from './system';
export * from './explanation';

// Backwards compatibility types
export type RiskState = 'SAFE' | 'WARNING' | 'DANGER';
export type RiskTrend = 'STABLE' | 'INCREASING' | 'DECREASING';
export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'WARNING';

export interface LegacyNodeStatus {
  node_id: string;
  zone_id: string;
  x: number;
  y: number;
  depth_m: number;
  latest_risk: number;
  state: RiskState;
  trend: RiskTrend;
  tilt_x: number;
  tilt_y: number;
  tilt_rate: number;
  vibration_intensity: number;
  stability_grade: string;
  precursor_stage: string;
  last_updated: string;
}

export interface RiskAssessment {
  id?: number;
  node_id: string;
  zone_id: string;
  timestamp: string;
  risk_score: number;
  state: RiskState;
  trend: RiskTrend;
  reasons?: string | string[];
}

export interface AlertEvent {
  event_id: string;
  node_id: string;
  zone_id: string;
  timestamp: string;
  severity: AlertSeverity;
  risk_score: number;
  state: RiskState;
  reason: string;
  affected_nodes: string[];
}
