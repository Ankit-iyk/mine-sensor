export interface Telemetry {
  node_id: string;
  zone_id: string;
  timestamp: string;
  tilt_x: number;
  tilt_y: number;
  tilt_magnitude: number;
  vibration: number;
  anomaly: number;
  accel_x?: number;
  accel_y?: number;
  accel_z?: number;
}
