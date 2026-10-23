export interface BackendAlertEvent {
  event_id?: string;
  node_id: string;
  zone_id: string;
  timestamp?: string;
  severity?: string;
  risk_score: number;
  state?: string;
  reason?: string;
  affected_nodes?: string[];
}

export type SubsenseStreamEvent = BackendAlertEvent | {
  event: 'risk_update';
  node_id: string;
  risk_score: number;
  state?: string;
  trend?: string;
};

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export class SubsenseWebSocketClient {
  private socket: WebSocket | null = null;
  private statusListeners = new Set<(status: ConnectionStatus) => void>();
  private eventListeners = new Set<(event: SubsenseStreamEvent) => void>();

  onStatusChange(listener: (status: ConnectionStatus) => void): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  subscribe(listener: (event: SubsenseStreamEvent) => void): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  connect(): void {
    const url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/alerts';
    this.setStatus('connecting');
    this.socket = new WebSocket(url);
    this.socket.onopen = () => this.setStatus('connected');
    this.socket.onclose = () => this.setStatus('disconnected');
    this.socket.onerror = () => this.setStatus('disconnected');
    this.socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as SubsenseStreamEvent;
      this.eventListeners.forEach((listener) => listener(event));
    };
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
    this.setStatus('disconnected');
  }

  private setStatus(status: ConnectionStatus): void {
    this.statusListeners.forEach((listener) => listener(status));
  }
}
