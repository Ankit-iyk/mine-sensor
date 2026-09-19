'use client';

import React from 'react';
import { NodeStatus as NodeStatusType } from '@/types/node';
import { getStatusConfig } from '@/lib/status-config';

interface NodeStatusProps {
  status: NodeStatusType | string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export function NodeStatus({
  status,
  size = 'md',
  showDot = true,
  className = '',
  style = {},
}: NodeStatusProps) {
  const config = getStatusConfig(status);

  const sizeStyles = {
    sm: {
      padding: '2px 6px',
      fontSize: '0.68rem',
      dotSize: '6px',
    },
    md: {
      padding: '3px 9px',
      fontSize: '0.74rem',
      dotSize: '8px',
    },
    lg: {
      padding: '4px 12px',
      fontSize: '0.85rem',
      dotSize: '10px',
    },
  }[size];

  return (
    <span
      role="status"
      aria-label={`Node Status: ${config.label}`}
      className={`node-status-badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontFamily: 'var(--font-mono, monospace)',
        fontWeight: 600,
        letterSpacing: '0.04em',
        borderRadius: 'var(--radius-sm, 4px)',
        backgroundColor: config.bgColor,
        color: config.textColor,
        border: `1px solid ${config.borderColor}`,
        padding: sizeStyles.padding,
        fontSize: sizeStyles.fontSize,
        textTransform: 'uppercase',
        lineHeight: 1.2,
        userSelect: 'none',
        ...style,
      }}
    >
      {showDot && (
        <span
          aria-hidden="true"
          style={{
            width: sizeStyles.dotSize,
            height: sizeStyles.dotSize,
            borderRadius: '50%',
            backgroundColor: config.color,
            boxShadow: `0 0 8px ${config.glowColor}`,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
      )}
      <span>{config.label}</span>
    </span>
  );
}
