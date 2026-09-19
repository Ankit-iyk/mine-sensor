export interface AlertExplanation {
  node_id: string;
  zone_id?: string;
  risk_score: number;
  trend: string;
  status: string;
  title: string;
  reasons: string[];
  metrics_summary?: {
    tilt_deviation?: string;
    vibration_level?: string;
    correlation_nodes?: string[];
    risk_velocity?: string;
  };
}
