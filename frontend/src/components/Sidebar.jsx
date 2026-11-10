import React, { useEffect, useState } from 'react';
import {
  Network,
  PlayCircle,
  BarChart3,
  History,
  Activity,
  Layers,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, topologyData }) {
  const [backendHealthy, setBackendHealthy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const checkHealth = async () => {
      try {
        const res = await fetch('/health');
        if (!cancelled) {
          setBackendHealthy(res.ok);
        }
      } catch (e) {
        if (!cancelled) setBackendHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const nodeCount = topologyData?.nodes?.length || 0;
  const linkCount = topologyData?.links?.length || 0;
  const topoType = topologyData?.metadata?.topology_type || 'Not Loaded';
  const seed = topologyData?.metadata?.seed;

  const navGroups = [
    {
      section: 'Workspace',
      links: [
        {
          id: 'builder',
          label: 'Network Builder',
          helper: 'Topology & parameter setup',
          icon: Network
        },
        {
          id: 'simulation',
          label: 'Simulation',
          helper: 'Interactive packet routing & faults',
          icon: PlayCircle
        },
        {
          id: 'optimization',
          label: 'Optimization & RL',
          helper: 'Comparative benchmarks & PPO',
          icon: BarChart3
        }
      ]
    },
    {
      section: 'Research',
      links: [
        {
          id: 'history',
          label: 'Experiment Ledger',
          helper: 'Auditable run logs & metrics',
          icon: History
        }
      ]
    }
  ];

  return (
    <aside className="app-sidebar" aria-label="Main Navigation">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Activity size={22} />
        </div>
        <div className="sidebar-brand-text">
          <span className="sidebar-brand-title">NETRA</span>
          <span className="sidebar-brand-desc">Network Engineering, Traffic Routing & Intelligence Platform</span>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="sidebar-nav">
        {navGroups.map((group) => (
          <div key={group.section} className="sidebar-nav-group">
            <div className="sidebar-section-heading">{group.section}</div>
            <div className="sidebar-nav-list">
              {group.links.map((link) => {
                const IconComponent = link.icon;
                const isActive = activeTab === link.id;
                return (
                  <button
                    key={link.id}
                    type="button"
                    className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => setActiveTab(link.id)}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <div className="nav-item-icon">
                      <IconComponent size={18} />
                    </div>
                    <div className="nav-item-content">
                      <span className="nav-item-label">{link.label}</span>
                      <span className="nav-item-helper">{link.helper}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Sidebar Footer: System Status and Network Summary */}
      <div className="sidebar-footer">
        {/* Network Telemetry Summary */}
        <div className="sidebar-network-summary">
          <div className="summary-title">
            <Layers size={14} />
            <span>Network Context</span>
          </div>
          {nodeCount > 0 ? (
            <div className="summary-details">
              <div className="summary-row">
                <span>Topology:</span>
                <strong style={{ textTransform: 'capitalize' }}>{topoType}</strong>
              </div>
              <div className="summary-row">
                <span>Nodes & Links:</span>
                <strong>{nodeCount} nodes &bull; {linkCount} links</strong>
              </div>
              {seed !== undefined && seed !== null && (
                <div className="summary-row">
                  <span>Random Seed:</span>
                  <span className="summary-mono-val">{seed}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="summary-empty">
              No active topology generated yet.
            </div>
          )}
        </div>

        {/* Backend Engine Health Status */}
        <div className="sidebar-system-status">
          <div
            className={`status-indicator-pill ${backendHealthy ? 'status-online' : 'status-offline'}`}
          >
            <span className="status-dot" />
            <span className="status-text">{backendHealthy ? 'Engine Online' : 'Engine Offline'}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
