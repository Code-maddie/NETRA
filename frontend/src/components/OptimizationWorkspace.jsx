import React, { useState, useEffect } from 'react';
import { BarChart3, Trophy, ArrowRight, Zap, Clock, ShieldCheck, AlertCircle, RefreshCw, Cpu, Award } from 'lucide-react';
import { api } from '../services/api';
import MetricsCards from './MetricsCards';

export default function OptimizationWorkspace({
  topologyData,
  sourceNode,
  destNode,
  topologyConfig
}) {
  const [evaluating, setEvaluating] = useState(false);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [timelineComparison, setTimelineComparison] = useState([]);
  const [traditionalAlgorithm, setTraditionalAlgorithm] = useState('dijkstra_dynamic');
  const [rlAlgorithm, setRlAlgorithm] = useState('ppo_residual');
  const [replicateCount, setReplicateCount] = useState(1);
  const [seedRuns, setSeedRuns] = useState([]);
  const [replicateProgress, setReplicateProgress] = useState('');
  const [selectedChartMetric, setSelectedChartMetric] = useState('latency');
  const [errorMessage, setErrorMessage] = useState(null);

  // RL Training state
  const [isTraining, setIsTraining] = useState(false);
  const [trainStatus, setTrainStatus] = useState(null);
  const [rlMetadata, setRlMetadata] = useState(null);

  useEffect(() => {
    // Fetch initial RL model status
    api.getRLStatus().then(setRlMetadata).catch(() => {});
  }, []);

  useEffect(() => {
    if (topologyConfig?.scenario === 'burst-congestion') {
      setTraditionalAlgorithm('dijkstra_static');
      setReplicateCount(5);
    } else {
      setReplicateCount(1);
    }
  }, [topologyConfig?.scenario]);

  const handleRunComparison = async () => {
    if (!topologyData) return;
    setEvaluating(true);
    setErrorMessage(null);
    setSeedRuns([]);

    try {
      const completedRuns = [];
      const firstSeed = Number(topologyConfig?.seed || 42);
      for (let index = 0; index < replicateCount; index += 1) {
        const seed = firstSeed + index;
        setReplicateProgress(`Running replicate ${index + 1} of ${replicateCount} (seed ${seed})`);
        const res = await api.evaluateOptimization({
          topology_data: topologyData,
          source: sourceNode,
          destination: destNode,
          traditional_algorithm: traditionalAlgorithm,
          rl_algorithm: rlAlgorithm,
          traffic_pattern: topologyConfig?.traffic_pattern || 'mixed',
          dynamic_conditions: topologyConfig?.dynamic_conditions ?? true,
          total_steps: topologyConfig?.steps || 30,
          seed
        });
        completedRuns.push({ seed, comparison: res.comparison });
        setSeedRuns([...completedRuns]);
        setComparisonResult(res.comparison);
        setTimelineComparison(res.timeline_comparison || []);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Optimization evaluation failed');
    } finally {
      setEvaluating(false);
      setReplicateProgress('');
    }
  };

  const handleTrainAgent = async () => {
    setIsTraining(true);
    setTrainStatus(null);
    try {
      const res = await api.trainRL({
        episodes: topologyConfig?.scenario === 'burst-congestion' ? 100 : 30,
        node_count: Math.min(50, topologyData?.nodes?.length || 20),
        topology_data: topologyData,
        source: sourceNode,
        destination: destNode,
        seed: topologyConfig?.seed || 42
      });
      setTrainStatus(res);
      // Refresh status
      const updatedStatus = await api.getRLStatus();
      setRlMetadata(updatedStatus);
    } catch (err) {
      setErrorMessage(err.message || 'PPO Training failed');
    } finally {
      setIsTraining(false);
    }
  };

  const trad = comparisonResult?.side_by_side?.traditional;
  const rl = comparisonResult?.side_by_side?.rl;
  const improvements = comparisonResult?.improvements;
  const meanMetric = (method, key) => {
    const values = seedRuns
      .map(({ comparison }) => comparison?.side_by_side?.[method]?.metrics)
      .filter((metrics) => metrics && (key !== 'avg_latency_ms' || metrics.packets_delivered > 0))
      .map((metrics) => Number(metrics[key]))
      .filter(Number.isFinite);
    return values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(key === 'routing_computation_time_ms' ? 4 : 2) : 'N/A';
  };
  const ppoWins = (key, lowerIsBetter) => seedRuns.filter(({ comparison }) => {
    const traditionalValue = Number(comparison?.side_by_side?.traditional?.metrics?.[key]);
    const ppoValue = Number(comparison?.side_by_side?.rl?.metrics?.[key]);
    if (!Number.isFinite(traditionalValue) || !Number.isFinite(ppoValue)) return false;
    return lowerIsBetter ? ppoValue < traditionalValue : ppoValue > traditionalValue;
  }).length;

  return (
    <div className="optimization-layout">
      {/* Full-width Comparative Evaluation Control Panel */}
      <section className="card config-panel" aria-labelledby="eval-panel-heading">
        <div className="card-header">
          <div>
            <div className="card-title" id="eval-panel-heading">
              <BarChart3 size={18} className="panel-icon" />
              <span>Comparative Routing Optimization &amp; Benchmarks</span>
            </div>
            <p className="card-subtitle">
              Synchronized head-to-head evaluation under identical topology, traffic demand, and dynamic conditions.
            </p>
          </div>
        </div>

        {/* Responsive Grid of Algorithm and Trial Selectors */}
        <div className="controls-grid controls-grid-3">
          <div className="form-group">
            <label htmlFor="baseline-algorithm-select">Baseline Routing Algorithm</label>
            <select
              id="baseline-algorithm-select"
              className="form-control"
              value={traditionalAlgorithm}
              onChange={(e) => setTraditionalAlgorithm(e.target.value)}
              disabled={evaluating}
            >
              <option value="dijkstra_dynamic">Baseline: Dijkstra (Delay-Sensitive)</option>
              <option value="cadj">Baseline: CADJ (Hysteresis Delay)</option>
              <option value="dijkstra_static">Baseline: Dijkstra (Static Shortest Path)</option>
              <option value="least_loaded">Baseline: Least-Loaded Routing</option>
            </select>
            <span className="input-helper">Deterministic baseline reference</span>
          </div>

          <div className="form-group">
            <label htmlFor="rl-algorithm-select">RL Candidate Policy</label>
            <select
              id="rl-algorithm-select"
              className="form-control"
              value={rlAlgorithm}
              onChange={(e) => setRlAlgorithm(e.target.value)}
              disabled={evaluating}
            >
              <option value="ppo_residual">NETRA V3: DAgger + Residual PPO</option>
              <option value="ppo_shielded">NETRA V3: PPO with Safety Fallback</option>
              <option value="ppo_legacy">RL: Legacy Per-Hop PPO</option>
            </select>
            <span className="input-helper">Actor-critic neural network agent</span>
          </div>

          <div className="form-group">
            <label htmlFor="replicate-count-select">Deterministic Seeds</label>
            <select
              id="replicate-count-select"
              className="form-control"
              value={replicateCount}
              onChange={(e) => setReplicateCount(Number(e.target.value))}
              disabled={evaluating}
            >
              <option value={1}>1 Trial (Exact current seed)</option>
              <option value={5}>5 Trials (Deterministic Monte Carlo)</option>
              <option value={10}>10 Trials (Robust statistical mean)</option>
            </select>
            <span className="input-helper">Statistical multi-seed verification</span>
          </div>
        </div>

        {/* Neural Network Policy Info Pill / Bar */}
        {rlMetadata && (
          <div className="policy-info-bar">
            <div className="policy-details">
              <span>Agent: <strong>{rlMetadata.algorithm}</strong></span>
              <span className="policy-separator">&bull;</span>
              <span>Status: <strong className={rlMetadata.trained ? 'text-success' : 'text-warning'}>
                {rlMetadata.trained ? `Trained policy (${rlMetadata.training_episodes || 0} episodes, VAL rel.cost: ${rlMetadata.best_val_score_pct}%)` : 'UNTRAINED — train before interpreting results'}
              </strong></span>
              <span className="policy-separator">&bull;</span>
              <span>Parameters: <strong>{rlMetadata.trainable_parameters?.toLocaleString()}</strong></span>
            </div>

            {trainStatus && (
              <div className="train-status-badge text-success">
                ✓ {trainStatus.mode === 'residual' ? `Trained ${trainStatus.episodes_trained} DAgger+PPO episodes (${trainStatus.mean_reward})` : `Trained ${trainStatus.episodes_trained} episodes &bull; Return: ${trainStatus.mean_reward}`}
              </div>
            )}
          </div>
        )}

        {/* Action Buttons Aligned at the Bottom */}
        <div className="card-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleTrainAgent}
            disabled={isTraining || !topologyData}
            title="Train Candidate DAgger + Residual PPO Network"
          >
            <Cpu size={16} />
            <span>{isTraining ? 'Training Residual PPO…' : 'Train Residual PPO'}</span>
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={handleRunComparison}
            disabled={evaluating || !topologyData}
          >
            {evaluating ? (
              <>
                <RefreshCw size={16} className="spin" />
                <span>{replicateProgress || 'Evaluating Models…'}</span>
              </>
            ) : (
              <>
                <Zap size={16} />
                <span>Run Head-to-Head Evaluation</span>
              </>
            )}
          </button>
        </div>
      </section>

      {/* Untrained Policy Warning Banner */}
      {rlMetadata && !rlMetadata.trained && (
        <div role="note" className="alert-banner alert-warning">
          <AlertCircle size={18} className="alert-icon" />
          <div className="alert-content">
            PPO is currently untrained. Run <strong>Train Residual PPO</strong> on this topology before treating its routing metrics as a meaningful comparison. A model architecture by itself does not produce optimal weights without training.
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div role="alert" className="alert-banner alert-error">
          <AlertCircle size={18} className="alert-icon" />
          <div className="alert-content">{errorMessage}</div>
        </div>
      )}

      {/* Multi-Seed Evidence Summary */}
      {seedRuns.length > 0 && (
        <section className="card evidence-panel" aria-label="Repeated-seed Evidence">
          <div className="card-header-compact">
            <div>
              <h3 className="section-title">Repeated-Seed Statistical Evidence ({seedRuns.length}/{replicateCount} runs)</h3>
              <p className="card-subtitle">
                Averaged across completed deterministic seeds {seedRuns.map(({ seed }) => seed).join(', ')}. Latency averages include runs with delivered packets. Each run is recorded in Experiment History.
              </p>
            </div>
          </div>
          <div className="evidence-grid">
            {[
              ['Mean packet loss', 'packet_loss_pct', '%', true],
              ['Mean throughput', 'throughput_mbps', 'Mbps', false],
              ['Mean delivered latency', 'avg_latency_ms', 'ms', true],
              ['Mean route compute time', 'routing_computation_time_ms', 'ms', true],
            ].map(([label, key, unit, lowerIsBetter]) => (
              <div key={key} className="evidence-card">
                <span className="evidence-label">{label.toUpperCase()}</span>
                <div className="evidence-value">
                  Dijkstra {meanMetric('traditional', key)} {unit} &bull; PPO {meanMetric('rl', key)} {unit}
                </div>
                <div className="evidence-win-count">
                  PPO better in <strong>{ppoWins(key, lowerIsBetter)}/{seedRuns.length}</strong> runs
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Side-by-Side Comparison Results Section */}
      {comparisonResult && (
        <section className="results-panel" aria-label="Comparison Results">
          {/* Honest Verdict Banner */}
          <div className={`verdict-card ${comparisonResult.winner?.includes('RL') ? 'verdict-rl' : 'verdict-baseline'}`}>
            <div className="verdict-header">
              <Trophy size={22} className="verdict-icon" />
              <h3 className="verdict-title">
                {seedRuns.length > 1 ? `Last replicate (seed ${seedRuns[seedRuns.length - 1]?.seed}): ` : 'Winner: '}
                {comparisonResult.winner}
              </h3>
            </div>
            <p className="verdict-text">{comparisonResult.verdict}</p>
            {comparisonResult.reasons && comparisonResult.reasons.length > 0 && (
              <ul className="verdict-reasons">
                {comparisonResult.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Side-by-Side Candidates Grid */}
          <div className="comparison-cards-grid">
            {/* Candidate A: Traditional Routing */}
            <div className={`card candidate-card ${comparisonResult.winner?.includes('Traditional') ? 'candidate-winner' : ''}`}>
              {comparisonResult.winner?.includes('Traditional') && (
                <div className="winner-tag">Lowest Cost Baseline</div>
              )}
              <div className="candidate-header">
                <span className="candidate-badge badge-baseline">Baseline</span>
                <h3 className="candidate-name">{trad?.algorithm || 'Traditional Routing'}</h3>
              </div>
              <p className="candidate-desc">
                Deterministic shortest path based on static link costs and dynamic queuing delay estimation.
              </p>

              <div className="candidate-metrics-grid">
                <div className="metric-box">
                  <span className="metric-box-label">AVG LATENCY</span>
                  <span className="metric-box-val val-blue">
                    {trad?.metrics?.packets_delivered === 0 ? 'N/A' : trad?.metrics?.avg_latency_ms}
                    {trad?.metrics?.packets_delivered === 0 ? '' : <span className="unit">ms</span>}
                  </span>
                </div>

                <div className="metric-box">
                  <span className="metric-box-label">PACKET LOSS</span>
                  <span className={`metric-box-val ${trad?.metrics?.packet_loss_pct > 0 ? 'val-error' : 'val-success'}`}>
                    {trad?.metrics?.packet_loss_pct}%
                  </span>
                </div>

                <div className="metric-box">
                  <span className="metric-box-label">THROUGHPUT</span>
                  <span className="metric-box-val">
                    {trad?.metrics?.throughput_mbps} <span className="unit">Mbps</span>
                  </span>
                </div>

                <div className="metric-box">
                  <span className="metric-box-label">COMPUTE TIME</span>
                  <span className="metric-box-val val-muted">
                    {trad?.metrics?.routing_computation_time_ms} <span className="unit">ms</span>
                  </span>
                </div>
              </div>

              <div className="candidate-path-box">
                <span className="path-label">Computed Path:</span>
                <span className="path-text">
                  {trad?.path?.slice(0, 8).join(' → ')}{trad?.path?.length > 8 ? ' …' : ''} ({trad?.hops} hops)
                </span>
              </div>
            </div>

            {/* Candidate B: PPO Reinforcement Learning */}
            <div className={`card candidate-card ${comparisonResult.winner?.includes('RL') ? 'candidate-winner' : ''}`}>
              {comparisonResult.winner?.includes('RL') && (
                <div className="winner-tag">Superior Adaptive Route</div>
              )}
              <div className="candidate-header">
                <span className="candidate-badge badge-rl">Candidate</span>
                <h3 className="candidate-name">Proximal Policy Optimization (PPO)</h3>
              </div>
              <p className="candidate-desc">
                Actor-Critic neural agent optimizing end-to-end latency, congestion penalties, and dynamic fault avoidance.
              </p>

              <div className="candidate-metrics-grid">
                <div className="metric-box">
                  <span className="metric-box-label">AVG LATENCY</span>
                  <span className="metric-box-val val-terracotta">
                    {rl?.metrics?.packets_delivered === 0 ? 'N/A' : rl?.metrics?.avg_latency_ms}
                    {rl?.metrics?.packets_delivered === 0 ? '' : <span className="unit">ms</span>}
                  </span>
                </div>

                <div className="metric-box">
                  <span className="metric-box-label">PACKET LOSS</span>
                  <span className={`metric-box-val ${rl?.metrics?.packet_loss_pct > 0 ? 'val-error' : 'val-success'}`}>
                    {rl?.metrics?.packet_loss_pct}%
                  </span>
                </div>

                <div className="metric-box">
                  <span className="metric-box-label">THROUGHPUT</span>
                  <span className="metric-box-val">
                    {rl?.metrics?.throughput_mbps} <span className="unit">Mbps</span>
                  </span>
                </div>

                <div className="metric-box">
                  <span className="metric-box-label">COMPUTE TIME</span>
                  <span className="metric-box-val val-muted">
                    {rl?.metrics?.routing_computation_time_ms} <span className="unit">ms</span>
                  </span>
                </div>
              </div>

              <div className="candidate-path-box">
                <span className="path-label">Computed Path:</span>
                <span className="path-text">
                  {rl?.path?.slice(0, 8).join(' → ')}{rl?.path?.length > 8 ? ' …' : ''} ({rl?.hops} hops)
                </span>
              </div>

              {rl?.metrics?.shield_fallback_rate_pct !== undefined && rl?.metrics?.shield_fallback_rate_pct !== null && (
                <div className="shield-fallback-pill">
                  <ShieldCheck size={15} />
                  <span>
                    Shield Fallback Rate: <strong>{rl.metrics.shield_fallback_rate_pct}%</strong> ({rl.metrics.shield_fallback_count} baseline fallbacks triggered)
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Time Series Telemetry Charts */}
          <div className="card chart-panel">
            <div className="card-header">
              <div className="card-title">
                <BarChart3 size={18} className="panel-icon" />
                <span>Comparative Step Timeline Telemetry</span>
              </div>

              <div className="chart-metric-buttons">
                <button
                  type="button"
                  className={`btn btn-sm ${selectedChartMetric === 'latency' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectedChartMetric('latency')}
                >
                  Latency (ms)
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${selectedChartMetric === 'loss' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectedChartMetric('loss')}
                >
                  Dropped Packets
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${selectedChartMetric === 'reward' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectedChartMetric('reward')}
                >
                  PPO Reward
                </button>
              </div>
            </div>

            {/* SVG Interactive Multi-Series Chart */}
            <div className="timeline-chart-wrapper">
              <TimelineChart
                data={timelineComparison}
                metric={selectedChartMetric}
              />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

// Lightweight, crisp SVG Timeline Chart Component adapted for warm neutral light theme
function TimelineChart({ data, metric }) {
  if (!data || data.length === 0) return null;

  const width = 1000;
  const height = 240;
  const padding = { top: 20, right: 30, bottom: 35, left: 50 };

  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  let yValA = d => d.traditional_latency_ms;
  let yValB = d => d.rl_latency_ms;
  let labelA = "Traditional (Dijkstra)";
  let labelB = "PPO Reinforcement Learning";
  let colorA = "#526B73"; // Muted blue-grey
  let colorB = "#8A5C45"; // Muted terracotta

  if (metric === 'loss') {
    yValA = d => d.traditional_dropped;
    yValB = d => d.rl_dropped;
    labelA = "Traditional Loss";
    labelB = "RL Loss";
    colorA = "#9F3A38"; // Restrained red
    colorB = "#A96B1E"; // Restrained amber
  } else if (metric === 'reward') {
    yValA = () => 0;
    yValB = d => d.rl_reward;
    labelA = "";
    labelB = "PPO Cumulative Reward";
    colorB = "#8A5C45";
  }

  const allVals = [];
  data.forEach(d => {
    if (metric !== 'reward') {
      const a = yValA(d);
      if (a !== null && a !== undefined && Number.isFinite(Number(a))) allVals.push(Number(a));
    }
    const b = yValB(d);
    if (b !== null && b !== undefined && Number.isFinite(Number(b))) allVals.push(Number(b));
  });

  const maxVal = Math.max(1, (allVals.length ? Math.max(...allVals) : 1) * 1.15);
  const minVal = Math.min(0, allVals.length ? Math.min(...allVals) : 0);
  const valRange = maxVal - minVal || 1;

  const getX = i => padding.left + (i / Math.max(1, data.length - 1)) * innerW;
  const getY = val => padding.top + innerH - ((Number(val) - minVal) / valRange) * innerH;
  const isValid = val => val !== null && val !== undefined && Number.isFinite(Number(val));
  const buildPath = selector => {
    let drawing = false;
    const segments = [];
    data.forEach((d, i) => {
      const value = selector(d);
      if (!isValid(value)) {
        drawing = false;
        return;
      }
      segments.push(`${drawing ? 'L' : 'M'} ${getX(i)} ${getY(value)}`);
      drawing = true;
    });
    return segments.join(' ');
  };
  const pathA = buildPath(yValA);
  const pathB = buildPath(yValB);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%', overflow: 'visible' }}>
      {/* Horizontal Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
        const y = padding.top + innerH * (1 - pct);
        const val = minVal + pct * valRange;
        return (
          <g key={idx}>
            <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="rgba(50, 50, 50, 0.08)" strokeDasharray="3 3" />
            <text x={padding.left - 8} y={y + 4} fill="#585552" fontSize="10" textAnchor="end" fontFamily="var(--font-mono)">
              {val.toFixed(1)}
            </text>
          </g>
        );
      })}

      {/* Axis lines */}
      <line x1={padding.left} y1={padding.top + innerH} x2={width - padding.right} y2={padding.top + innerH} stroke="rgba(50, 50, 50, 0.25)" />

      {/* Series A (Traditional) */}
      {metric !== 'reward' && (
        <path d={pathA} fill="none" stroke={colorA} strokeWidth="2.5" />
      )}

      {/* Series B (RL) */}
      <path d={pathB} fill="none" stroke={colorB} strokeWidth="2.5" />

      {/* Points */}
      {data.map((d, i) => (
        <g key={i}>
          {metric !== 'reward' && isValid(yValA(d)) && (
            <circle cx={getX(i)} cy={getY(yValA(d))} r="3" fill={colorA} />
          )}
          {isValid(yValB(d)) && <circle cx={getX(i)} cy={getY(yValB(d))} r="3.5" fill={colorB} />}
        </g>
      ))}

      {/* Legend */}
      <g transform={`translate(${width - 280}, 15)`}>
        {metric !== 'reward' && (
          <g>
            <line x1="0" y1="0" x2="18" y2="0" stroke={colorA} strokeWidth="3" />
            <text x="24" y="4" fill="#323232" fontSize="11" fontWeight="600" fontFamily="var(--font-heading)">{labelA}</text>
          </g>
        )}
        <g transform={`translate(${metric !== 'reward' ? 0 : 70}, ${metric !== 'reward' ? 18 : 0})`}>
          <line x1="0" y1="0" x2="18" y2="0" stroke={colorB} strokeWidth="3" />
          <text x="24" y="4" fill="#8A5C45" fontSize="11" fontWeight="600" fontFamily="var(--font-heading)">{labelB}</text>
        </g>
      </g>
    </svg>
  );
}
