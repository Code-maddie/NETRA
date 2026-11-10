import React, { useState, useEffect } from 'react';
import { AlertTriangle, LoaderCircle, RefreshCw } from 'lucide-react';
import Sidebar from './components/Sidebar';
import NetworkBuilder from './components/NetworkBuilder';
import SimulationWorkspace from './components/SimulationWorkspace';
import OptimizationWorkspace from './components/OptimizationWorkspace';
import ExperimentHistory from './components/ExperimentHistory';
import NodeLinkDrawer from './components/NodeLinkDrawer';
import { api } from './services/api';

const PAGE_METADATA = {
  builder: {
    section: 'Workspace',
    title: 'Network Builder',
    description: 'Configure synthetic network topologies, parameter benchmarks, and routing endpoints.'
  },
  simulation: {
    section: 'Workspace',
    title: 'Simulation Workspace',
    description: 'Interactive step-by-step routing simulation with dynamic link failures and congestion telemetry.'
  },
  optimization: {
    section: 'Workspace',
    title: 'Optimization & RL Comparison',
    description: 'Synchronized head-to-head evaluation comparing deterministic routing baselines against Proximal Policy Optimization (PPO).'
  },
  history: {
    section: 'Research',
    title: 'Experiment Ledger',
    description: 'Auditable records of completed simulation runs, deterministic seeds, and comparative evaluation logs.'
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState('builder');

  // Master topology configuration (Initialized with PRD reference benchmark)
  const [topologyConfig, setTopologyConfig] = useState({
    node_count: 25, // Start with responsive 25 nodes for instant visual feedback, 685 benchmark preset readily available
    topology_type: 'random',
    density: 'high',
    seed: 42,
    traffic_pattern: 'mixed',
    dynamic_conditions: true,
    steps: 30
  });

  const [topologyData, setTopologyData] = useState(null);
  const [initializing, setInitializing] = useState(true);
  const [startupError, setStartupError] = useState('');
  const [sourceNode, setSourceNode] = useState(0);
  const [destNode, setDestNode] = useState(24);

  // Inspector Drawer state
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedLink, setSelectedLink] = useState(null);

  // Load initial topology on startup
  useEffect(() => {
    let cancelled = false;
    const initTopology = async () => {
      setInitializing(true);
      setStartupError('');
      try {
        const res = await api.generateTopology({
          node_count: 25,
          topology_type: 'random',
          density: 'high',
          seed: 42
        });
        if (!cancelled) setTopologyData(res.data);
      } catch (e) {
        console.error('Failed to load initial topology:', e);
        if (!cancelled) setStartupError(e.message || 'Could not connect to the NETRA backend.');
      } finally {
        if (!cancelled) setInitializing(false);
      }
    };
    initTopology();
    return () => { cancelled = true; };
  }, []);

  const retryInitialLoad = async () => {
    setInitializing(true);
    setStartupError('');
    try {
      const res = await api.generateTopology({
        node_count: topologyConfig.node_count,
        topology_type: topologyConfig.topology_type,
        density: topologyConfig.density,
        seed: topologyConfig.seed
      });
      setTopologyData(res.data);
    } catch (e) {
      setStartupError(e.message || 'Could not connect to the NETRA backend.');
    } finally {
      setInitializing(false);
    }
  };

  const handleSelectNode = (node) => {
    setSelectedNode(node);
    setSelectedLink(null);
  };

  const handleSelectLink = (link) => {
    setSelectedLink(link);
    setSelectedNode(null);
  };

  const handleCloseDrawer = () => {
    setSelectedNode(null);
    setSelectedLink(null);
  };

  const currentPage = PAGE_METADATA[activeTab] || PAGE_METADATA.builder;

  return (
    <div className="netra-layout">
      {/* Persistent Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        topologyData={topologyData}
      />

      {/* Flexible Main Workspace */}
      <div className="main-workspace">
        {/* Workspace Top Header: Section, Title, and One-sentence Description */}
        <header className="workspace-header">
          <div className="workspace-header-content">
            <span className="workspace-breadcrumb">{currentPage.section}</span>
            <h1 className="workspace-title">{currentPage.title}</h1>
            <p className="workspace-description">{currentPage.description}</p>
          </div>
        </header>

        {/* Workspace Content Area (Independently Scrollable) */}
        <main className="workspace-body">
          {initializing && (
            <div role="status" className="status-notice status-notice-loading">
              <LoaderCircle size={18} className="spin" />
              <span>Connecting to NETRA and loading the starter network…</span>
            </div>
          )}

          {startupError && (
            <div role="alert" className="status-notice status-notice-error">
              <AlertTriangle size={18} className="notice-icon" />
              <div className="notice-text">
                <strong>NETRA could not load the network.</strong>
                <div>{startupError}</div>
                <div className="notice-hint">Start the backend using the setup steps in README.md, then retry.</div>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={retryInitialLoad}
                disabled={initializing}
              >
                <RefreshCw size={14} /> Retry
              </button>
            </div>
          )}

          {activeTab === 'builder' && (
            <NetworkBuilder
              topologyConfig={topologyConfig}
              setTopologyConfig={setTopologyConfig}
              topologyData={topologyData}
              setTopologyData={setTopologyData}
              sourceNode={sourceNode}
              setSourceNode={setSourceNode}
              destNode={destNode}
              setDestNode={setDestNode}
              onLaunchSimulation={() => setActiveTab('simulation')}
              onLaunchOptimization={() => setActiveTab('optimization')}
            />
          )}

          {activeTab === 'simulation' && (
            <SimulationWorkspace
              topologyData={topologyData}
              sourceNode={sourceNode}
              destNode={destNode}
              topologyConfig={topologyConfig}
              onSelectNode={handleSelectNode}
              onSelectLink={handleSelectLink}
              selectedNode={selectedNode}
              selectedLink={selectedLink}
            />
          )}

          {activeTab === 'optimization' && (
            <OptimizationWorkspace
              topologyData={topologyData}
              sourceNode={sourceNode}
              destNode={destNode}
              topologyConfig={topologyConfig}
            />
          )}

          {activeTab === 'history' && (
            <ExperimentHistory />
          )}
        </main>
      </div>

      {/* Slide-out Node / Link Telemetry Drawer */}
      <NodeLinkDrawer
        selectedNode={selectedNode}
        selectedLink={selectedLink}
        topologyData={topologyData}
        onClose={handleCloseDrawer}
      />
    </div>
  );
}
