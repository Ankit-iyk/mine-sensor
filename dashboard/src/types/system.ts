import { NodeStatus } from './node';

export interface SystemStatus {
  overall_mine_status: NodeStatus;
  active_nodes: number;
  total_nodes: number;
  warning_nodes: number;
  active_incidents: number;
  system_health_percent: number;
  mqtt_status: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING';
  backend_status: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  db_status: 'HEALTHY' | 'SYNCING' | 'OFFLINE';
  is_demo_mode: boolean;
  last_updated: string;
}

export interface SystemHealth {
  status: 'online' | 'degraded' | 'offline';
  version?: string;
  mqtt_connected?: boolean;
  db_connected?: boolean;
  active_nodes_count?: number;
}
