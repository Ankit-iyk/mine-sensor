export type NodeStatus = 'SAFE' | 'WARNING' | 'DANGER' | 'OFFLINE' | 'UNKNOWN';

export interface NodePosition {
  x: number;
  y: number;
  depth_m?: number;
}

export interface MineNode {
  node_id: string;
  zone_id: string;
  status: NodeStatus;
  risk_score: number;
  trend: 'STABLE' | 'ESCALATING' | 'DECREASING' | 'PERSISTENT' | 'UNKNOWN';
  position: NodePosition;
  tilt_x: number;
  tilt_y: number;
  vibration: number;
  anomaly_score: number;
  last_updated: string;
}

// Alias for backwards compatibility with previous NodeStatus interface
export type Node = MineNode;
