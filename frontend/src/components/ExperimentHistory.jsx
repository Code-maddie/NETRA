import React, { useState, useEffect } from 'react';
import { History, Eye, Trash2, RefreshCw, Layers, Calendar, Cpu } from 'lucide-react';
import { api } from '../services/api';

export default function ExperimentHistory() {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedExp, setSelectedExp] = useState(null);

  const fetchExperiments = async () => {
    setLoading(true);
    try {
      const res = await api.listExperiments(50);
      setExperiments(res.experiments || []);
    } catch (e) {
      // Handle error gracefully
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  const handleDelete = async (expId, e) => {
    e.stopPropagation();
    try {
      await api.deleteExperiment(expId);
      setExperiments(prev => prev.filter(x => x.id !== expId));
      if (selectedExp?.id === expId) setSelectedExp(null);
    } catch (err) {
      // Error handling
    }
  };

  return (
    <div className="history-layout">
      {/* Ledger Container Card */}
      <section className="card ledger-panel" aria-labelledby="ledger-heading">
        <div className="card-header">
          <div>
            <div className="card-title" id="ledger-heading">
              <History size={18} className="panel-icon" />
              <span>Experiment Ledger &amp; Reproducibility Audit</span>
            </div>
            <p className="card-subtitle">
              Auditable records of completed simulation runs and head-to-head algorithm comparisons with deterministic seeds.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchExperiments}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh Ledger</span>
          </button>
        </div>

        {/* Experiments Table with Responsive Horizontal Scrolling */}
        {experiments.length === 0 ? (
          <div className="empty-state-panel">
            <History size={36} className="empty-icon" />
            <h3 className="empty-title">No Experiments Recorded</h3>
            <p className="empty-desc">
              Run a simulation or benchmark in the Network Builder or Optimization tabs to generate audit records.
            </p>
          </div>
        ) : (
          <div className="responsive-table-wrapper" tabIndex="0" role="region" aria-label="Experiment history table">
            <table className="custom-table">
              <thead>
                <tr>
                  <th scope="col">Experiment</th>
                  <th scope="col">Date &amp; Time</th>
                  <th scope="col">Network Config</th>
                  <th scope="col">Traffic Pattern</th>
                  <th scope="col">Winner / Outcome</th>
                  <th scope="col" className="table-actions-header">Actions</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp) => {
                  const net = exp.network_config || {};
                  const comp = exp.comparison || {};
                  const isSelected = selectedExp?.id === exp.id;
                  return (
                    <tr
                      key={exp.id}
                      onClick={() => setSelectedExp(exp)}
                      className={`table-row ${isSelected ? 'row-selected' : ''}`}
                    >
                      <td className="cell-primary">
                        <div className="exp-name">{exp.name}</div>
                        <div className="exp-id">ID: {exp.id}</div>
                        {!exp.evaluation_version && (
                          <div className="legacy-notice">
                            Legacy result &bull; Rerun with corrected metrics
                          </div>
                        )}
                      </td>

                      <td className="cell-date">
                        <div className="date-text">{exp.created_at}</div>
                      </td>

                      <td className="cell-config">
                        <span className="config-nodes">{net.node_count} nodes</span>
                        <span className="config-type">&bull; {net.topology_type}</span>
                        <div className="config-seed">Seed: {net.seed}</div>
                      </td>

                      <td className="cell-traffic">
                        <span className="traffic-pattern">{exp.traffic_config?.pattern}</span>
                        <span className="traffic-steps">({exp.traffic_config?.steps} steps)</span>
                      </td>

                      <td className="cell-outcome">
                        <span className={`outcome-pill ${comp.winner?.includes('RL') ? 'outcome-rl' : 'outcome-baseline'}`}>
                          {comp.winner || 'Completed Run'}
                        </span>
                      </td>

                      <td className="cell-actions">
                        <div className="action-button-group">
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedExp(exp);
                            }}
                            title="Inspect Experiment Details"
                            aria-label={`View details for ${exp.name}`}
                          >
                            <Eye size={12} />
                            <span>View</span>
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn-xs"
                            onClick={(e) => handleDelete(exp.id, e)}
                            title="Delete Record"
                            aria-label={`Delete experiment ${exp.name}`}
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Selected Experiment Detail Card (Full-width Below Table) */}
      {selectedExp && (
        <section className="card inspection-panel" aria-labelledby="inspection-heading">
          <div className="card-header">
            <div>
              <div className="card-title" id="inspection-heading">
                <Layers size={18} className="panel-icon" />
                <span>Experiment Details: {selectedExp.name}</span>
              </div>
              <span className="badge-pill">ID: {selectedExp.id}</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedExp(null)}
            >
              Close Details
            </button>
          </div>

          <div className="inspection-grid">
            <div className="inspection-tile">
              <span className="tile-label">TOPOLOGY &amp; SCALE</span>
              <div className="tile-main-val">
                {selectedExp.network_config?.node_count} Nodes ({selectedExp.network_config?.topology_type})
              </div>
              <span className="tile-sub">Configured graph size</span>
            </div>

            <div className="inspection-tile">
              <span className="tile-label">ROUTING ENDPOINTS</span>
              <div className="tile-main-val text-success">
                Node {selectedExp.network_config?.source} &rarr; Node {selectedExp.network_config?.destination}
              </div>
              <span className="tile-sub">Verified source-destination pair</span>
            </div>

            <div className="inspection-tile">
              <span className="tile-label">DETERMINISTIC SEED</span>
              <div className="tile-main-val val-mono">
                {selectedExp.network_config?.seed}
              </div>
              <span className="tile-sub">Reproducibility seed</span>
            </div>
          </div>

          {!selectedExp.evaluation_version && (
            <div role="note" className="alert-banner alert-warning" style={{ marginTop: '1rem' }}>
              This experiment predates the routing and metric fixes. Its historical scores are retained for audit purposes, but rerun the comparison before using them as evidence.
            </div>
          )}

          {selectedExp.notes && (
            <div className="inspection-notes-box">
              <strong>Analytical Findings:</strong> {selectedExp.notes}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
