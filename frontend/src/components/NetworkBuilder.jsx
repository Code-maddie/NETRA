import React, { useState } from 'react';
import { Network, Sparkles, CheckCircle2, AlertTriangle, ShieldAlert, Sliders, ArrowRight } from 'lucide-react';
import { api } from '../services/api';

export default function NetworkBuilder({
  topologyConfig,
  setTopologyConfig,
  topologyData,
  setTopologyData,
  sourceNode,
  setSourceNode,
  destNode,
  setDestNode,
  onLaunchSimulation,
  onLaunchOptimization
}) {
  const [loading, setLoading] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleGenerate = async (overrideConfig = null, specialScenario = null) => {
    const configToUse = overrideConfig || topologyConfig;
    if (!specialScenario && configToUse.scenario) {
      const { scenario, ...regularConfig } = configToUse;
      setTopologyConfig(regularConfig);
    }
    setLoading(true);
    setErrorMessage(null);
    setValidationResult(null);

    try {
      const res = specialScenario === 'burst-congestion'
        ? await api.generateBurstCongestionDemo()
        : await api.generateTopology({
        node_count: parseInt(configToUse.node_count),
        topology_type: configToUse.topology_type,
        density: configToUse.density,
        seed: parseInt(configToUse.seed) || 42
      });

      setTopologyData(res.data);

      const maxId = res.data.nodes.length - 1;
      const nextSource = specialScenario === 'burst-congestion'
        ? 0
        : (sourceNode > maxId || sourceNode < 0 ? 0 : parseInt(sourceNode));
      const nextDestination = specialScenario === 'burst-congestion'
        ? maxId
        : (destNode > maxId || destNode === nextSource ? Math.max(1, Math.min(maxId, 50)) : parseInt(destNode));
      setSourceNode(nextSource);
      setDestNode(nextDestination);

      // Automatically validate reachability for the endpoints selected by the preset.
      const val = await api.validateNetwork({
        topology_data: res.data,
        source: nextSource,
        destination: nextDestination
      });
      setValidationResult(val);

    } catch (err) {
      setErrorMessage(err.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!topologyData) {
      setErrorMessage('Please generate a topology first before validating.');
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      const val = await api.validateNetwork({
        topology_data: topologyData,
        source: parseInt(sourceNode),
        destination: parseInt(destNode)
      });
      setValidationResult(val);
    } catch (err) {
      setErrorMessage(err.message || 'Validation error');
    } finally {
      setLoading(false);
    }
  };

  const loadPreset = (presetType) => {
    let cfg;
    if (presetType === 'burst_congestion') {
      cfg = {
        node_count: 5,
        topology_type: 'random',
        density: 'medium',
        seed: 42,
        traffic_pattern: 'bursty',
        dynamic_conditions: false,
        steps: 42,
        scenario: 'burst-congestion'
      };
      setSourceNode(0);
      setDestNode(4);
    } else if (presetType === '685_benchmark') {
      // PRD Section 8 reference benchmark
      cfg = {
        node_count: 685,
        topology_type: 'random',
        density: 'high',
        seed: 42,
        traffic_pattern: 'mixed',
        dynamic_conditions: true,
        steps: 30
      };
      setSourceNode(1);
      setDestNode(50);
    } else if (presetType === '1000_max') {
      cfg = {
        node_count: 1000,
        topology_type: 'random',
        density: 'medium',
        seed: 99,
        traffic_pattern: 'mixed',
        dynamic_conditions: true,
        steps: 30
      };
      setSourceNode(0);
      setDestNode(999);
    } else if (presetType === 'single_node') {
      cfg = {
        node_count: 1,
        topology_type: 'random',
        density: 'low',
        seed: 1,
        traffic_pattern: 'constant',
        dynamic_conditions: false,
        steps: 10
      };
      setSourceNode(0);
      setDestNode(0);
    } else {
      // 25 nodes quick demo
      cfg = {
        node_count: 25,
        topology_type: 'random',
        density: 'high',
        seed: 101,
        traffic_pattern: 'bursty',
        dynamic_conditions: true,
        steps: 25
      };
      setSourceNode(0);
      setDestNode(24);
    }

    setTopologyConfig(cfg);
    handleGenerate(cfg, presetType === 'burst_congestion' ? 'burst-congestion' : null);
  };

  const isSingleNode = topologyConfig.node_count === 1;

  return (
    <div className="builder-layout">
      {/* Full-width Configuration Area */}
      <section className="card config-panel" aria-labelledby="config-panel-heading">
        <div className="card-header">
          <div className="card-title" id="config-panel-heading">
            <Sliders size={18} className="panel-icon" />
            <span>Network Topology Configuration</span>
          </div>
          <span className="badge-pill">
            Node Range: [1 &ndash; 1,000]
          </span>
        </div>

        {/* Quick Benchmarks & Presets Row near the top */}
        <div className="config-section">
          <div className="section-label">Quick Benchmarks &amp; Reference Presets</div>
          <div className="preset-row">
            <button
              type="button"
              className={`preset-btn ${topologyConfig.scenario === 'burst-congestion' ? 'preset-active' : ''}`}
              onClick={() => loadPreset('burst_congestion')}
              title="Two-route network with a burst-sensitive bottleneck"
            >
              <span className="preset-count">5 Nodes</span>
              <span className="preset-title">Burst Congestion</span>
              <span className="preset-desc">PPO bottleneck demo</span>
            </button>

            <button
              type="button"
              className={`preset-btn ${topologyConfig.node_count === 685 && !topologyConfig.scenario ? 'preset-active' : ''}`}
              onClick={() => loadPreset('685_benchmark')}
              title="PRD Reference Configuration"
            >
              <span className="preset-count">685 Nodes</span>
              <span className="preset-title">PRD Benchmark</span>
              <span className="preset-desc">Reference scale setup</span>
            </button>

            <button
              type="button"
              className={`preset-btn ${topologyConfig.node_count === 1000 ? 'preset-active' : ''}`}
              onClick={() => loadPreset('1000_max')}
              title="Full 1,000 Node Scalability Test"
            >
              <span className="preset-count">1,000 Nodes</span>
              <span className="preset-title">Scale Limit</span>
              <span className="preset-desc">Maximum stress test</span>
            </button>

            <button
              type="button"
              className={`preset-btn ${topologyConfig.node_count === 25 && !topologyConfig.scenario ? 'preset-active' : ''}`}
              onClick={() => loadPreset('demo_25')}
              title="25 Nodes Interactive Demo"
            >
              <span className="preset-count">25 Nodes</span>
              <span className="preset-title">Quick Demo</span>
              <span className="preset-desc">Fast responsive trial</span>
            </button>

            <button
              type="button"
              className={`preset-btn ${topologyConfig.node_count === 1 ? 'preset-active' : ''}`}
              onClick={() => loadPreset('single_node')}
              title="1 Node Boundary Test"
            >
              <span className="preset-count">1 Node</span>
              <span className="preset-title">Boundary Test</span>
              <span className="preset-desc">Section 5.1 edge case</span>
            </button>
          </div>
        </div>

        {/* Special Scenario Advisory */}
        {topologyConfig.scenario === 'burst-congestion' && (
          <div role="note" className="alert-banner alert-warning">
            <AlertTriangle size={18} className="alert-icon" />
            <div className="alert-content">
              <strong>Controlled PPO demonstration:</strong> The two-hop route has a 100 Mbps bottleneck; the three-hop alternate has 1 Gbps links. Bursty traffic tests whether a trained PPO policy avoids congestion. Dynamic link failures are off so the traffic effect is isolated. This scenario is a hypothesis to evaluate, not a guaranteed PPO win.
            </div>
          </div>
        )}

        {/* Tidy Responsive Controls Grid */}
        <div className="controls-grid">
          {/* Column 1: Node Count */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="node-count-slider">Node Count (N)</label>
              <span className="control-val-badge">{topologyConfig.node_count} Nodes</span>
            </div>
            <input
              id="node-count-slider"
              type="range"
              min="1"
              max="1000"
              step="1"
              className="form-range"
              value={topologyConfig.node_count}
              onChange={(e) => setTopologyConfig({ ...topologyConfig, node_count: parseInt(e.target.value) || 1 })}
              aria-label="Node count slider"
            />
            <div className="input-with-hint">
              <input
                id="node-count-input"
                type="number"
                min="1"
                max="1000"
                className="form-control"
                value={topologyConfig.node_count}
                onChange={(e) => {
                  const val = Math.max(1, Math.min(1000, parseInt(e.target.value) || 1));
                  setTopologyConfig({ ...topologyConfig, node_count: val });
                }}
                aria-label="Node count numeric value"
              />
              <span className="input-helper">Range: 1 to 1000</span>
            </div>
          </div>

          {/* Column 2: Topology Structure & Density */}
          <div className="form-group">
            <label htmlFor="topology-type-select">Topology Structure</label>
            <select
              id="topology-type-select"
              className="form-control"
              value={topologyConfig.topology_type}
              onChange={(e) => setTopologyConfig({ ...topologyConfig, topology_type: e.target.value })}
            >
              <option value="random">Random Network</option>
              <option value="scale_free">Scale-Free (Barabási-Albert)</option>
              <option value="mesh">Mesh (Dense Interconnected)</option>
              <option value="star">Star (Central Hub)</option>
              <option value="ring">Ring (Circular Loop)</option>
              <option value="line">Line (Linear Bus)</option>
              <option value="grid">Grid (2D Lattice)</option>
            </select>

            <label htmlFor="topology-density-select" style={{ marginTop: '0.75rem' }}>Connection Density</label>
            <select
              id="topology-density-select"
              className="form-control"
              value={topologyConfig.density}
              onChange={(e) => setTopologyConfig({ ...topologyConfig, density: e.target.value })}
              disabled={topologyConfig.topology_type !== 'random'}
            >
              <option value="low">Low (Avg degree ~2-3)</option>
              <option value="medium">Medium (Avg degree ~4-6)</option>
              <option value="high">High (Avg degree ~8-12)</option>
            </select>
          </div>

          {/* Column 3: Routing Endpoints */}
          <div className="form-group">
            <label>Routing Endpoints</label>
            <div className="endpoints-pair">
              <div>
                <span className="sub-label">Source Node</span>
                <input
                  type="number"
                  min="0"
                  max={Math.max(0, (topologyData?.nodes?.length || 1) - 1)}
                  className="form-control"
                  value={sourceNode}
                  onChange={(e) => setSourceNode(parseInt(e.target.value) || 0)}
                  disabled={isSingleNode}
                  aria-label="Source node index"
                />
              </div>
              <div>
                <span className="sub-label">Destination Node</span>
                <input
                  type="number"
                  min="0"
                  max={Math.max(0, (topologyData?.nodes?.length || 1) - 1)}
                  className="form-control"
                  value={destNode}
                  onChange={(e) => setDestNode(parseInt(e.target.value) || 0)}
                  disabled={isSingleNode}
                  aria-label="Destination node index"
                />
              </div>
            </div>
            <span className="input-helper">Max node ID: {Math.max(0, (topologyData?.nodes?.length || 1) - 1)}</span>
          </div>

          {/* Column 4: Traffic Pattern & Deterministic Seed */}
          <div className="form-group">
            <label htmlFor="traffic-pattern-select">Traffic Pattern</label>
            <select
              id="traffic-pattern-select"
              className="form-control"
              value={topologyConfig.traffic_pattern || 'mixed'}
              onChange={(e) => setTopologyConfig({ ...topologyConfig, traffic_pattern: e.target.value })}
            >
              <option value="mixed">Mixed (Diurnal Oscillations + High Bursts)</option>
              <option value="bursty">Bursty (Poisson Arrival Spikes)</option>
              <option value="random_bursts">Random Bursts</option>
              <option value="periodic">Periodic (Sinusoidal Load Wave)</option>
              <option value="constant">Constant (Steady Rate)</option>
            </select>

            <div className="form-label-row" style={{ marginTop: '0.75rem' }}>
              <label htmlFor="random-seed-input">Random Seed</label>
              <span className="input-helper">Deterministic</span>
            </div>
            <input
              id="random-seed-input"
              type="number"
              className="form-control"
              value={topologyConfig.seed || 42}
              onChange={(e) => setTopologyConfig({ ...topologyConfig, seed: parseInt(e.target.value) || 42 })}
              aria-label="Random seed"
            />
          </div>
        </div>

        {/* Dynamic Conditions Row */}
        <div className="checkbox-row">
          <label className="checkbox-container">
            <input
              type="checkbox"
              className="custom-checkbox"
              checked={topologyConfig.dynamic_conditions ?? true}
              onChange={(e) => setTopologyConfig({ ...topologyConfig, dynamic_conditions: e.target.checked })}
            />
            <span className="checkbox-label">
              <strong>Dynamic Network Faults:</strong> Enable stochastic link degradation and dynamic line drops during execution
            </span>
          </label>
        </div>

        {/* Action Buttons Aligned at the Bottom */}
        <div className="card-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleValidate}
            disabled={loading || !topologyData}
          >
            Validate Connectivity
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleGenerate({ ...topologyConfig, scenario: undefined })}
            disabled={loading}
          >
            <Sparkles size={16} />
            <span>{loading ? 'Generating Network…' : 'Generate Network'}</span>
          </button>
        </div>
      </section>

      {/* Full-width Results & Telemetry Area (Below Configuration Panel) */}
      <section className="results-panel" aria-label="Generated Network Telemetry and Status">
        {/* Error Alert */}
        {errorMessage && (
          <div role="alert" className="alert-banner alert-error">
            <ShieldAlert size={20} className="alert-icon" />
            <div className="alert-content">{errorMessage}</div>
          </div>
        )}

        {/* Single-Node Boundary Case Note */}
        {isSingleNode && (
          <div role="note" className="alert-banner alert-warning">
            <AlertTriangle size={20} className="alert-icon" />
            <div className="alert-content">
              <strong>Single-Node Boundary Condition:</strong> Generated 1-node network.
              As specified in PRD Section 5.1, topology generation and validation succeed, but a two-endpoint routing simulation requires at least 2 distinct nodes.
            </div>
          </div>
        )}

        {/* Topology Summary Panel */}
        {topologyData && (
          <div className="card telemetry-card">
            <div className="card-header">
              <div className="card-title">
                <Network size={18} className="panel-icon" />
                <span>Generated Topology Telemetry</span>
              </div>
              <span className="badge-pill">
                Seed: {topologyData.metadata?.seed}
              </span>
            </div>

            {/* Metrics Tiles Grid */}
            <div className="telemetry-grid">
              <div className="telemetry-tile">
                <span className="tile-label">TOTAL NODES</span>
                <span className="tile-value value-primary">{topologyData.metadata?.node_count}</span>
                <span className="tile-sub">Active vertices</span>
              </div>

              <div className="telemetry-tile">
                <span className="tile-label">ACTIVE LINKS</span>
                <span className="tile-value value-secondary">{topologyData.metadata?.link_count}</span>
                <span className="tile-sub">Network edges</span>
              </div>

              <div className="telemetry-tile">
                <span className="tile-label">AVG DEGREE</span>
                <span className="tile-value value-accent">{topologyData.metadata?.average_degree || 0}</span>
                <span className="tile-sub">Edges per node</span>
              </div>

              <div className="telemetry-tile">
                <span className="tile-label">CONNECTIVITY</span>
                <span className={`tile-value ${topologyData.metadata?.is_connected ? 'value-success' : 'value-error'}`}>
                  {topologyData.metadata?.is_connected ? 'Connected' : 'Disconnected'}
                </span>
                <span className="tile-sub">Global graph reach</span>
              </div>
            </div>

            {/* Validation Outcome Banner */}
            {validationResult && (
              <div className={`validation-banner ${validationResult.valid ? 'validation-valid' : 'validation-invalid'}`}>
                {validationResult.valid ? (
                  <CheckCircle2 size={18} className="validation-icon valid-icon" />
                ) : (
                  <AlertTriangle size={18} className="validation-icon invalid-icon" />
                )}
                <div className="validation-text">
                  {validationResult.valid ? (
                    <span>
                      <strong>Route Verified:</strong> Path exists between Node {sourceNode} and Node {destNode} with a minimum of {validationResult.details?.min_hops} hops.
                    </span>
                  ) : (
                    <span>
                      <strong>Validation Failure:</strong> {validationResult.errors?.join('; ')}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Next Action Gateways Aligned at Bottom */}
            <div className="card-actions gateways-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onLaunchOptimization}
                disabled={isSingleNode || (validationResult && !validationResult.valid)}
              >
                <span>Run Traditional vs RL Comparison</span>
                <ArrowRight size={16} />
              </button>

              <button
                type="button"
                className="btn btn-primary"
                onClick={onLaunchSimulation}
                disabled={isSingleNode || (validationResult && !validationResult.valid)}
              >
                <span>Launch Simulation Workspace</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
