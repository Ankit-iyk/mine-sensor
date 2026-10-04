export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'WARNING';
export type IncidentStatus = 'ACTIVE' | 'RESOLVED' | 'INVESTIGATING';

export interface Incident {
  id: number | string;
  node_id: string;
  zone_id: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  risk_score: number;
  trend?: 'ESCALATING' | 'PERSISTENT' | 'STABLE' | 'DECREASING';
  created_at: string;
  reason: string;
  resolved_at?: string | null;
  affected_nodes?: string[] | string;
}
