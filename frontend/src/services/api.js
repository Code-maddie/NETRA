/**
 * NETRA API Client Service
 * Centralizes all REST and WebSocket interactions with the FastAPI backend.
 */

const API_BASE = '/api';

export const api = {
  // Topology APIs
  async generateTopology(config) {
    const res = await fetch(`${API_BASE}/topology/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.errors?.join(', ') || err.detail || 'Topology generation failed');
    }
    return res.json();
  },

  async generateBurstCongestionDemo() {
    const res = await fetch(`${API_BASE}/topology/demo/burst-congestion`, { method: 'POST' });
    if (!res.ok) throw new Error('Could not load the burst-congestion demo topology');
    return res.json();
  },

  async validateNetwork(payload) {
    const res = await fetch(`${API_BASE}/topology/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Validation failed');
    }
    return res.json();
  },

  async getPresets() {
    const res = await fetch(`${API_BASE}/topology/presets`);
    if (!res.ok) throw new Error('Failed to fetch presets');
    return res.json();
  },

  // Simulation APIs
  async startSimulation(payload) {
    const res = await fetch(`${API_BASE}/simulation/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.errors?.join(', ') || err.detail || 'Simulation start failed');
    }
    return res.json();
  },

  async stepSimulation(simId) {
    const res = await fetch(`${API_BASE}/simulation/${simId}/step`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Step failed');
    return res.json();
  },

  async runSimulation(simId) {
    const res = await fetch(`${API_BASE}/simulation/${simId}/run`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Run all steps failed');
    return res.json();
  },

  async stopSimulation(simId) {
    const res = await fetch(`${API_BASE}/simulation/${simId}/stop`, {
      method: 'POST'
    });
    return res.json();
  },

  async getMetrics(simId) {
    const res = await fetch(`${API_BASE}/simulation/${simId}/metrics`);
    return res.json();
  },

  async getEvents(simId) {
    const res = await fetch(`${API_BASE}/simulation/${simId}/events`);
    return res.json();
  },

  // Optimization & RL APIs
  async evaluateOptimization(payload) {
    const res = await fetch(`${API_BASE}/optimization/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.errors?.join(', ') || err.detail || 'Optimization evaluation failed');
    }
    return res.json();
  },

  async runOptimization(payload) {
    const res = await fetch(`${API_BASE}/optimization/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.errors?.join(', ') || err.detail || 'Optimization failed');
    }
    return res.json();
  },

  async getRLStatus() {
    const res = await fetch(`${API_BASE}/rl/status`);
    return res.json();
  },

  async trainRL(payload) {
    const res = await fetch(`${API_BASE}/rl/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Training failed');
    }
    return res.json();
  },

  async getRLCheckpoints() {
    const res = await fetch(`${API_BASE}/rl/checkpoints`);
    if (!res.ok) throw new Error('Failed to fetch RL checkpoints');
    return res.json();
  },

  // Experiment Storage APIs
  async listExperiments(limit = 50) {
    const res = await fetch(`${API_BASE}/experiments?limit=${limit}`);
    return res.json();
  },

  async getExperiment(expId) {
    const res = await fetch(`${API_BASE}/experiments/${expId}`);
    return res.json();
  },

  async deleteExperiment(expId) {
    const res = await fetch(`${API_BASE}/experiments/${expId}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  async compareExperiments(expIdA, expIdB) {
    const res = await fetch(`${API_BASE}/experiments/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ experiment_id_a: expIdA, experiment_id_b: expIdB })
    });
    return res.json();
  }
};
