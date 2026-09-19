'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { RiskPoint } from '@/types/risk';
import { TrendingUp, Activity } from 'lucide-react';

interface RiskTrajectoryChartProps {
  nodeId: string;
  currentRisk: number;
  trend: string;
  trajectory: RiskPoint[];
}

export function RiskTrajectoryChart({
  nodeId,
  currentRisk,
  trend,
  trajectory,
}: RiskTrajectoryChartProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize ECharts instance if not already initialized
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current, undefined, {
        renderer: 'canvas',
      });
    }

    const chart = chartInstanceRef.current;

    const timestamps = trajectory.map((p) => p.timestamp);
    const riskValues = trajectory.map((p) => p.risk_score);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(14, 20, 32, 0.95)',
        borderColor: 'rgba(255, 255, 255, 0.15)',
        borderWidth: 1,
        textStyle: {
          color: '#f8fafc',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 12,
        },
        formatter: (params: unknown) => {
          const item = Array.isArray(params) ? params[0] : params;
          if (!item) return '';
          const p = item as { name: string; value: number };
          const riskColor = p.value >= 70 ? '#ef4444' : p.value >= 40 ? '#f59e0b' : '#10b981';
          return `
            <div style="font-family: JetBrains Mono, monospace; padding: 2px 4px;">
              <div style="color: #94a3b8; font-size: 11px; margin-bottom: 4px;">Time: ${p.name}</div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${riskColor};"></span>
                <span style="font-weight: 700;">Risk Score: ${p.value}</span>
              </div>
            </div>
          `;
        },
      },
      grid: {
        top: 25,
        right: 20,
        bottom: 25,
        left: 42,
      },
      xAxis: {
        type: 'category',
        data: timestamps,
        boundaryGap: false,
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.12)',
          },
        },
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
        },
        axisTick: {
          show: false,
        },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        interval: 25,
        axisLine: {
          show: false,
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.05)',
            type: 'dashed',
          },
        },
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
        },
      },
      series: [
        {
          name: 'Risk Score',
          type: 'line',
          smooth: 0.35,
          data: riskValues,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: {
            color: '#f59e0b',
            borderColor: '#ffffff',
            borderWidth: 1.5,
          },
          lineStyle: {
            width: 3,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#10b981' },
              { offset: 0.6, color: '#f59e0b' },
              { offset: 1, color: '#ef4444' },
            ]),
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(245, 158, 11, 0.35)' },
              { offset: 0.8, color: 'rgba(16, 185, 129, 0.05)' },
              { offset: 1, color: 'rgba(0, 0, 0, 0)' },
            ]),
          },
          markLine: {
            silent: true,
            symbol: ['none', 'none'],
            data: [
              {
                yAxis: 40,
                lineStyle: {
                  color: 'rgba(245, 158, 11, 0.4)',
                  type: 'dotted',
                  width: 1,
                },
                label: {
                  show: true,
                  position: 'insideEndTop',
                  formatter: 'WARNING (40)',
                  color: 'rgba(245, 158, 11, 0.7)',
                  fontSize: 9,
                  fontFamily: 'monospace',
                },
              },
              {
                yAxis: 70,
                lineStyle: {
                  color: 'rgba(239, 68, 68, 0.4)',
                  type: 'dotted',
                  width: 1,
                },
                label: {
                  show: true,
                  position: 'insideEndTop',
                  formatter: 'DANGER (70)',
                  color: 'rgba(239, 68, 68, 0.7)',
                  fontSize: 9,
                  fontFamily: 'monospace',
                },
              },
            ],
          },
        },
      ],
    };

    chart.setOption(option);

    // Responsive resize handler
    const handleResize = () => {
      chart.resize();
    };

    window.addEventListener('resize', handleResize);
    const observer = new ResizeObserver(() => chart.resize());
    if (chartRef.current) observer.observe(chartRef.current);

    return () => {
      window.removeEventListener('resize', handleResize);
      observer.disconnect();
    };
  }, [trajectory]);

  // Clean up chart instance on unmount
  useEffect(() => {
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose();
        chartInstanceRef.current = null;
      }
    };
  }, []);

  return (
    <div
      className="glass-panel"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Card Header with Current & Trend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: '10px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} color="var(--color-warning, #f59e0b)" />
            <h2
              style={{
                fontSize: '0.95rem',
                fontWeight: 700,
                letterSpacing: '0.02em',
                textTransform: 'uppercase',
                color: '#ffffff',
                margin: 0,
              }}
            >
              RISK TRAJECTORY
            </h2>
            <span
              style={{
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono, monospace)',
                color: 'var(--text-secondary, #94a3b8)',
                background: 'rgba(255, 255, 255, 0.06)',
                padding: '2px 6px',
                borderRadius: '4px',
              }}
            >
              Node {nodeId}
            </span>
          </div>
          <p
            style={{
              fontSize: '0.74rem',
              color: 'var(--text-muted, #64748b)',
              marginTop: '3px',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            Temporal progression of subsidence probability
          </p>
        </div>

        {/* Current Risk & Trend Callout */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            backgroundColor: 'rgba(0, 0, 0, 0.35)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '0.66rem',
                color: 'var(--text-muted, #64748b)',
                textTransform: 'uppercase',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              Current
            </div>
            <div
              style={{
                fontSize: '1.25rem',
                fontWeight: 800,
                fontFamily: 'var(--font-mono, monospace)',
                color: currentRisk >= 70 ? '#ef4444' : currentRisk >= 40 ? '#f59e0b' : '#10b981',
                lineHeight: 1.1,
              }}
            >
              {currentRisk}
            </div>
          </div>

          <div
            style={{
              height: '24px',
              width: '1px',
              backgroundColor: 'var(--border-subtle, rgba(255,255,255,0.1))',
            }}
          />

          <div>
            <div
              style={{
                fontSize: '0.66rem',
                color: 'var(--text-muted, #64748b)',
                textTransform: 'uppercase',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              Trend
            </div>
            <div
              style={{
                fontSize: '0.8rem',
                fontWeight: 700,
                fontFamily: 'var(--font-mono, monospace)',
                color: trend === 'ESCALATING' ? '#f59e0b' : '#34d399',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <TrendingUp size={13} />
              {trend}
            </div>
          </div>
        </div>
      </div>

      {/* ECharts Container */}
      <div
        ref={chartRef}
        style={{
          width: '100%',
          height: '260px',
          minHeight: '260px',
        }}
        role="region"
        aria-label="ECharts Risk Trajectory Progression Graph"
      />

      {/* Fictional Disclaimer */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.64rem',
          color: 'var(--text-muted, #64748b)',
          fontFamily: 'var(--font-mono, monospace)',
          borderTop: '1px solid var(--border-subtle, rgba(255,255,255,0.06))',
          paddingTop: '8px',
          marginTop: '6px',
        }}
      >
        <span>Model: Temporal LSTM Precursor Evaluator</span>
        <span>* Simulated trajectory validation data</span>
      </div>
    </div>
  );
}
