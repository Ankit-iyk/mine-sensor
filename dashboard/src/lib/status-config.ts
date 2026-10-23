interface StatusConfig {
  label: string;
  color: string;
  glowColor: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}

const config: Record<string, StatusConfig> = {
  SAFE: {
    label: 'SAFE',
    color: '#22c55e',
    glowColor: 'rgba(34, 197, 94, 0.5)',
    bgColor: 'rgba(34, 197, 94, 0.12)',
    textColor: '#86efac',
    borderColor: 'rgba(34, 197, 94, 0.35)',
  },
  WARNING: {
    label: 'WARNING',
    color: '#f59e0b',
    glowColor: 'rgba(245, 158, 11, 0.5)',
    bgColor: 'rgba(245, 158, 11, 0.12)',
    textColor: '#fcd34d',
    borderColor: 'rgba(245, 158, 11, 0.35)',
  },
  DANGER: {
    label: 'DANGER',
    color: '#ef4444',
    glowColor: 'rgba(239, 68, 68, 0.5)',
    bgColor: 'rgba(239, 68, 68, 0.12)',
    textColor: '#fca5a5',
    borderColor: 'rgba(239, 68, 68, 0.35)',
  },
  OFFLINE: {
    label: 'OFFLINE',
    color: '#94a3b8',
    glowColor: 'rgba(148, 163, 184, 0.3)',
    bgColor: 'rgba(148, 163, 184, 0.12)',
    textColor: '#cbd5e1',
    borderColor: 'rgba(148, 163, 184, 0.35)',
  },
  UNKNOWN: {
    label: 'UNKNOWN',
    color: '#94a3b8',
    glowColor: 'rgba(148, 163, 184, 0.3)',
    bgColor: 'rgba(148, 163, 184, 0.12)',
    textColor: '#cbd5e1',
    borderColor: 'rgba(148, 163, 184, 0.35)',
  },
};

export function getStatusConfig(status: string): StatusConfig {
  return config[status] || config.UNKNOWN;
}
