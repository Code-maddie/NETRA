import React from 'react';
import { Clock, Zap, AlertOctagon, CheckCheck, Gauge, Cpu, Award } from 'lucide-react';

export default function MetricsCards({ metrics, deltas = null }) {
  if (!metrics) return null;
  const hasLatencySamples = Number(metrics.packets_delivered || 0) > 0;

  return (
    <div className="metrics-cards-grid">
      {/* Average Latency */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">Average Latency</span>
          <Clock size={16} className="metric-icon icon-terracotta" />
        </div>
        <div className="metric-value-row">
          <span className="metric-num">{hasLatencySamples ? metrics.avg_latency_ms : 'N/A'}</span>
          {hasLatencySamples && <span className="metric-unit">ms</span>}
        </div>
        {deltas?.latency_improvement_pct !== undefined ? (
          <div className={`metric-delta ${deltas.latency_improvement_pct >= 0 ? 'delta-positive' : 'delta-negative'}`}>
            {deltas.latency_improvement_pct >= 0 ? '↓' : '↑'} {Math.abs(deltas.latency_improvement_pct)}% vs Baseline
          </div>
        ) : (
          <span className="metric-subtitle">Mean end-to-end trip time</span>
        )}
      </div>

      {/* 95th Percentile Latency */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">P95 Latency</span>
          <Clock size={16} className="metric-icon icon-bluegrey" />
        </div>
        <div className="metric-value-row">
          <span className="metric-num">{hasLatencySamples ? metrics.p95_latency_ms : 'N/A'}</span>
          {hasLatencySamples && <span className="metric-unit">ms</span>}
        </div>
        <span className="metric-subtitle">Tail delay experience</span>
      </div>

      {/* Throughput */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">Throughput</span>
          <Zap size={16} className="metric-icon icon-bluegrey" />
        </div>
        <div className="metric-value-row">
          <span className="metric-num">{metrics.throughput_mbps ?? 0}</span>
          <span className="metric-unit">Mbps</span>
        </div>
        <span className="metric-subtitle">
          {metrics.throughput_pps ? `${metrics.throughput_pps} pps delivered` : 'Active transmission'}
        </span>
      </div>

      {/* Packet Loss */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">Packet Loss Rate</span>
          <AlertOctagon size={16} className={`metric-icon ${metrics.packet_loss_pct > 0 ? 'icon-error' : 'icon-success'}`} />
        </div>
        <div className="metric-value-row">
          <span className={`metric-num ${metrics.packet_loss_pct > 0 ? 'text-error' : 'text-success'}`}>
            {metrics.packet_loss_pct ?? 0}%
          </span>
        </div>
        <span className="metric-subtitle">
          {metrics.packets_dropped ?? 0} / {metrics.packets_offered ?? 0} packets dropped
        </span>
      </div>

      {/* Delivery Success Rate */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">Delivery Rate</span>
          <CheckCheck size={16} className="metric-icon icon-success" />
        </div>
        <div className="metric-value-row">
          <span className="metric-num text-success">
            {metrics.delivery_success_rate_pct ?? 0}%
          </span>
        </div>
        <span className="metric-subtitle">
          {metrics.packets_delivered ?? 0} packets confirmed
        </span>
      </div>

      {/* Mean Link Utilization */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">Avg Link Utilization</span>
          <Gauge size={16} className="metric-icon icon-warning" />
        </div>
        <div className="metric-value-row">
          <span className="metric-num">{metrics.avg_link_utilization_pct ?? 0}%</span>
        </div>
        <span className="metric-subtitle">
          Peak link load: {metrics.max_link_utilization_pct ?? 0}%
        </span>
      </div>

      {/* Routing Computation Overhead */}
      <div className="card metric-card">
        <div className="metric-header">
          <span className="metric-title">Computation Time</span>
          <Cpu size={16} className="metric-icon icon-muted" />
        </div>
        <div className="metric-value-row">
          <span className="metric-num">{metrics.routing_computation_time_ms ?? 0}</span>
          <span className="metric-unit">ms</span>
        </div>
        <span className="metric-subtitle">Algorithm compute overhead</span>
      </div>

      {/* RL Reward if available */}
      {metrics.rl_reward !== null && metrics.rl_reward !== undefined && (
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">RL Return / Reward</span>
            <Award size={16} className="metric-icon icon-terracotta" />
          </div>
          <div className="metric-value-row">
            <span className="metric-num text-terracotta">
              {metrics.rl_reward}
            </span>
          </div>
          <span className="metric-subtitle">Policy objective scalar return</span>
        </div>
      )}
    </div>
  );
}
