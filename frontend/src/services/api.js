/**
 * API Service Layer for Multi-Agent AI Workflow Automation Platform.
 * Communicates directly with the FastAPI backend.
 */

// Fall back to direct backend URL if not proxied or specified via env
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Perform a health check query against the backend.
 * @returns {Promise<{ status: string, database: string, app_env: string, version: string }>}
 */
export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Execute a multi-agent workflow run.
 * @param {string} query - The user query to execute.
 * @returns {Promise<{ request_id: string, answer: string, key_points: string[], confidence: number, errors: string[] }>}
 */
export async function executeWorkflow(query) {
  if (!query || !query.trim()) {
    throw new Error('Query cannot be empty');
  }

  const response = await fetch(`${API_BASE_URL}/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ query: query.trim() }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = data?.detail || `Workflow request failed with HTTP ${response.status}`;
    throw new Error(errorMsg);
  }

  return data;
}

/**
 * Fetch paginated history of workflow runs.
 * @param {number} page
 * @param {number} pageSize
 * @returns {Promise<{ items: Array, total: number, page: number, page_size: number }>}
 */
export async function fetchWorkflowRuns(page = 1, pageSize = 10) {
  const response = await fetch(`${API_BASE_URL}/workflows?page=${page}&page_size=${pageSize}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load workflow runs (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch full details and execution steps for a single workflow run.
 * @param {string} runId
 * @returns {Promise<Object>}
 */
export async function fetchWorkflowRunDetail(runId) {
  if (!runId) throw new Error('runId is required');

  const response = await fetch(`${API_BASE_URL}/workflows/${runId}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch workflow run detail (HTTP ${response.status})`);
  }

  return response.json();
}
