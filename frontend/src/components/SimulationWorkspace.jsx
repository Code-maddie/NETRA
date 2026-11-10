import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, StepForward, Square, RotateCcw, Radio, Terminal, AlertTriangle, ShieldCheck } from 'lucide-react';
import GraphViewer from './GraphViewer';
import MetricsCards from './MetricsCards';
import { api } from '../services/api';

export default function SimulationWorkspace({
  topologyData,
  sourceNode,
  destNode,
  topologyConfig,
  onSelectNode,
  onSelectLink,
  selectedNode,
  selectedLink
}) {
  const [simId, setSimId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(30);
  const [activePath, setActivePath] = useState([]);
  const [events, setEvents] = useState([]);
  const [latestStepMetrics, setLatestStepMetrics] = useState(null);
  const [summaryMetrics, setSummaryMetrics] = useState(null);
  const [stepSpeedMs, setStepSpeedMs] = useState(400);
  const [routingAlgorithm, setRoutingAlgorithm] = useState('dijkstra_dynamic');
  const [statusMessage, setStatusMessage] = useState(null);

  const timerRef = useRef(null);

  // Initialize or Reset simulation
  const handleStartOrReset = async () => {
    if (!topologyData) return;
    clearInterval(timerRef.current);
    setIsRunning(false);
    setStatusMessage(null);
    setEvents([]);
    setCurrentStep(0);
    setSummaryMetrics(null);

    try {
      const res = await api.startSimulation({
        topology_data: topologyData,
        source: sourceNode,
        destination: destNode,
        routing_method: routingAlgorithm,
        traffic_pattern: topologyConfig?.traffic_pattern || 'mixed',
        dynamic_conditions: topologyConfig?.dynamic_conditions ?? true,
        total_steps: topologyConfig?.steps || 30,
        seed: topologyConfig?.seed || 42
      });

      setSimId(res.simulation_id);
      setTotalSteps(res.total_steps);
      if (res.initial_event) {
        setEvents([res.initial_event]);
      }
      setIsRunning(true);
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to start simulation' });
    }
  };

  // Perform a single step
  const handleStep = async () => {
    if (!simId) {
      await handleStartOrReset();
      return;
    }

    try {
      const res = await api.stepSimulation(simId);
      setCurrentStep(res.step + 1);
      setActivePath(res.active_path || []);
      setLatestStepMetrics(res.step_metrics);

      if (res.events_emitted && res.events_emitted.length > 0) {
        setEvents(prev => [...prev, ...res.events_emitted]);
      }

      if (res.is_completed) {
        setIsRunning(false);
        clearInterval(timerRef.current);
        const summary = await api.getMetrics(simId);
        setSummaryMetrics(summary.metrics);
      }
    } catch (err) {
      setIsRunning(false);
      clearInterval(timerRef.current);
      setStatusMessage({ type: 'error', text: err.message || 'Step execution failed' });
    }
  };

  // Auto-play interval effect
  useEffect(() => {
    if (isRunning && simId) {
      timerRef.current = setInterval(() => {
        handleStep();
      }, stepSpeedMs);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRunning, simId, stepSpeedMs]);

  const togglePause = () => {
    setIsRunning(prev => !prev);
  };

  const handleStop = async () => {
    setIsRunning(false);
    clearInterval(timerRef.current);
    if (simId) {
      try {
        const res = await api.stopSimulation(simId);
        if (res.summary) {
          setSummaryMetrics(res.summary.metrics);
        }
      } catch (e) {
        // Stop silently
      }
    }
  };

  return (
    <div className="simulation-layout">
      {/* Full-width Simulation Controls Bar */}
      <section className="card playback-panel" aria-label="Simulation Controls">
        <div className="playback-bar-inner">
          {/* Primary transport buttons */}
          <div className="playback-actions">
            {!simId || (!isRunning && currentStep === 0) ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleStartOrReset}
              >
                <Play size={16} />
                <span>Start Simulation</span>
              </button>
            ) : isRunning ? (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={togglePause}
              >
                <Pause size={16} />
                <span>Pause</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={togglePause}
              >
                <Play size={16} />
                <span>Resume</span>
              </button>
            )}

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleStep}
              disabled={isRunning || currentStep >= totalSteps}
              title="Step Forward One Step"
            >
              <StepForward size={16} />
              <span>Step</span>
            </button>

            <button
              type="button"
              className="btn btn-danger"
              onClick={handleStop}
              disabled={!simId}
              title="Stop Simulation"
            >
              <Square size={16} />
              <span>Stop</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary btn-icon-only"
              onClick={handleStartOrReset}
              title="Reset to Step 0"
              aria-label="Reset simulation"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          {/* Telemetry settings: Algorithm, Step counter, Speed */}
          <div className="playback-settings">
            <div className="step-counter-pill">
              <span className="step-label">Step</span>
              <strong className="step-value">{currentStep} / {totalSteps}</strong>
            </div>

            <div className="setting-item">
              <label htmlFor="routing-algorithm-select" className="setting-label">Algorithm:</label>
              <select
                id="routing-algorithm-select"
                className="form-control select-compact"
                value={routingAlgorithm}
                onChange={(e) => setRoutingAlgorithm(e.target.value)}
                disabled={isRunning}
              >
                <option value="ppo_residual">NETRA V3: DAgger + Residual PPO</option>
                <option value="ppo_shielded">NETRA V3: PPO with Safety Fallback</option>
                <option value="cadj">CADJ (Hysteresis Delay-Sensitive)</option>
                <option value="dijkstra_dynamic">Dijkstra (Dynamic Delay-Sensitive)</option>
                <option value="dijkstra_static">Dijkstra (Static Hop Cost)</option>
                <option value="least_loaded">Least-Loaded Routing</option>
                <option value="ppo_legacy">Legacy Per-Hop PPO</option>
              </select>
            </div>

            <div className="setting-item">
              <label htmlFor="playback-speed-slider" className="setting-label">Speed:</label>
              <input
                id="playback-speed-slider"
                type="range"
                min="100"
                max="1000"
                step="50"
                className="form-range speed-slider"
                value={stepSpeedMs}
                onChange={(e) => setStepSpeedMs(parseInt(e.target.value))}
                aria-label="Simulation speed in milliseconds"
              />
              <span className="speed-readout">{stepSpeedMs}ms</span>
            </div>

            <div className="traffic-live-badge">
              <Radio size={14} className="badge-icon" />
              <span>LIVE TRAFFIC</span>
            </div>
          </div>
        </div>
      </section>

      {/* Status Message */}
      {statusMessage && (
        <div role="alert" className="alert-banner alert-error">
          <AlertTriangle size={18} className="alert-icon" />
          <div className="alert-content">{statusMessage.text}</div>
        </div>
      )}

      {/* Main View: Graph Canvas & Live Event Log */}
      <div className="simulation-workspace-grid">
        {/* Interactive Graph Canvas */}
        <div className="canvas-column">
          <GraphViewer
            topologyData={topologyData}
            sourceNode={sourceNode}
            destNode={destNode}
            activePath={activePath}
            onSelectNode={onSelectNode}
            onSelectLink={onSelectLink}
            selectedNode={selectedNode}
            selectedLink={selectedLink}
          />
        </div>

        {/* Live Verifiable Event Stream & Path Info */}
        <div className="telemetry-column">
          {/* Active Route Card */}
          <div className="card route-card">
            <div className="card-header-compact">
              <span className="compact-title">Current Traversed Route</span>
              <span className="compact-badge">Node Flow</span>
            </div>

            {activePath && activePath.length > 0 ? (
              <div className="route-content">
                <div className="route-nodes-list">
                  {activePath.map((nodeId, idx) => (
                    <span
                      key={idx}
                      className={`route-node-pill ${nodeId === sourceNode ? 'node-source' : (nodeId === destNode ? 'node-destination' : 'node-intermediate')}`}
                    >
                      {nodeId}
                    </span>
                  ))}
                </div>
                <div className="route-stats">
                  <span>Hops: <strong>{activePath.length - 1}</strong></span>
                  <span className="stat-separator">&bull;</span>
                  <span>Latency: <strong>{latestStepMetrics?.packets_delivered === 0 ? 'N/A' : latestStepMetrics?.avg_latency_ms} {latestStepMetrics?.packets_delivered === 0 ? '' : 'ms'}</strong></span>
                </div>
              </div>
            ) : (
              <div className="route-empty">
                Awaiting simulation step execution to trace route.
              </div>
            )}
          </div>

          {/* Real-Time Verifiable Event Terminal */}
          <div className="card terminal-card">
            <div className="card-header-compact">
              <div className="terminal-title">
                <Terminal size={14} className="panel-icon" />
                <span>Simulation Event Log</span>
              </div>
              <span className="badge-pill">
                {events.length} Events
              </span>
            </div>

            <div className="event-terminal" tabIndex="0" role="log" aria-label="Real-time simulation event stream">
              {events.length === 0 ? (
                <div className="terminal-placeholder">
                  Press Start or Step to begin simulation telemetry…
                </div>
              ) : (
                events.map((ev, i) => (
                  <div key={i} className="event-entry">
                    <span className="event-step-pill">t={ev.step}</span>
                    <span className={`event-type-tag event-${ev.type}`}>[{ev.type}]</span>
                    <span className="event-detail">
                      {ev.details?.reason || (ev.details?.link_id ? `Link ${ev.details.link_id}` : (ev.details?.packets_offered ? `${ev.details.packets_offered} packets burst` : JSON.stringify(ev.details)))}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Summary Metrics Section (Spanning Content Width) */}
      {summaryMetrics && (
        <section className="results-panel" aria-label="Completed Simulation Metrics">
          <div className="section-header">
            <h2 className="section-title">Completed Simulation Metrics Summary</h2>
            <p className="section-desc">End-of-run network performance telemetry across latency, throughput, loss, and compute overhead.</p>
          </div>
          <MetricsCards metrics={summaryMetrics} />
        </section>
      )}
    </div>
  );
}
