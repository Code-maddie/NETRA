import React from 'react';
import { X, Network, Share2, Activity, HardDrive, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function NodeLinkDrawer({
  selectedNode,
  selectedLink,
  topologyData,
  onClose
}) {
  const isOpen = Boolean(selectedNode || selectedLink);

  return (
    <aside
      className={`inspector-drawer ${isOpen ? 'open' : ''}`}
      aria-label="Component Telemetry Inspector"
      aria-hidden={!isOpen}
    >
      <div className="drawer-header">
        <div className="drawer-title">
          <Activity size={18} className="panel-icon" />
          <h2>
            {selectedNode ? `Node Inspector: #${selectedNode.id}` : (selectedLink ? `Link Inspector: ${selectedLink.id}` : 'Inspector')}
          </h2>
        </div>
        <button
          type="button"
          className="drawer-close-btn"
          onClick={onClose}
          aria-label="Close inspector drawer"
        >
          <X size={18} />
        </button>
      </div>

      {/* Node Details */}
      {selectedNode && (
        <div className="drawer-content">
          <div className="drawer-hero-box">
            <span className="drawer-hero-label">Node Identifier</span>
            <div className="drawer-hero-val">Node #{selectedNode.id}</div>
          </div>

          <div className="drawer-stats-grid">
            <div className="drawer-stat-tile">
              <span className="stat-label">DEGREE</span>
              <div className="stat-val">{selectedNode.degree || 0} Links</div>
            </div>

            <div className="drawer-stat-tile">
              <span className="stat-label">COORDINATES</span>
              <div className="stat-val font-mono">
                ({Math.round(selectedNode.x)}, {Math.round(selectedNode.y)})
              </div>
            </div>
          </div>

          {/* Connected Links / Neighbors */}
          <div className="drawer-section">
            <span className="drawer-section-title">Connected Neighbor Nodes</span>
            <div className="neighbors-list">
              {topologyData?.links
                ?.filter(l => l.source === selectedNode.id || l.target === selectedNode.id)
                ?.map(l => {
                  const neighborId = l.source === selectedNode.id ? l.target : l.source;
                  const isFailed = l.status === 'failed';
                  return (
                    <span
                      key={l.id}
                      className={`neighbor-pill ${isFailed ? 'pill-failed' : ''}`}
                    >
                      &rarr; Node {neighborId} {isFailed ? '(FAULT)' : ''}
                    </span>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      {/* Link Details */}
      {selectedLink && (
        <div className="drawer-content">
          <div className="drawer-hero-box">
            <span className="drawer-hero-label">Link Span</span>
            <div className="drawer-hero-val">
              Node {selectedLink.source} &harr; Node {selectedLink.target}
            </div>
          </div>

          {/* Link Status Banner */}
          <div className={`drawer-status-banner ${selectedLink.status === 'active' ? 'status-active' : 'status-failed'}`}>
            {selectedLink.status === 'active' ? (
              <CheckCircle2 size={16} />
            ) : (
              <ShieldAlert size={16} />
            )}
            <span>Link Status: {selectedLink.status?.toUpperCase()}</span>
          </div>

          <div className="drawer-stats-grid">
            <div className="drawer-stat-tile">
              <span className="stat-label">CAPACITY</span>
              <div className="stat-val font-mono">
                {selectedLink.capacity_mbps} <span className="unit">Mbps</span>
              </div>
            </div>

            <div className="drawer-stat-tile">
              <span className="stat-label">BASE DELAY</span>
              <div className="stat-val font-mono">
                {selectedLink.base_delay_ms} <span className="unit">ms</span>
              </div>
            </div>

            <div className="drawer-stat-tile">
              <span className="stat-label">CURRENT UTILIZATION</span>
              <div className={`stat-val font-mono ${(selectedLink.utilization || 0) >= 0.8 ? 'text-error' : 'text-success'}`}>
                {Math.round((selectedLink.utilization || 0) * 100)}%
              </div>
            </div>

            <div className="drawer-stat-tile">
              <span className="stat-label">QUEUE OCCUPANCY</span>
              <div className="stat-val font-mono text-warning">
                {selectedLink.queue_occupancy || 0} <span className="unit">pkts</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
