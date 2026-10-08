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
 * Fetch aggregated metrics across all workflow runs for the dashboard.
 * @returns {Promise<{ total_runs: number, active_runs: number, awaiting_approval: number, completed_runs: number, failed_runs: number, rejected_runs: number, avg_duration_ms: number|null }>}
 */
export async function fetchWorkflowStats() {
  const response = await fetch(`${API_BASE_URL}/workflows/stats`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load workflow stats (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch paginated history of workflow runs with optional status and search filters.
 * @param {number} page
 * @param {number} pageSize
 * @param {string|null} status
 * @param {string|null} search
 * @returns {Promise<{ items: Array, total: number, page: number, page_size: number }>}
 */
export async function fetchWorkflowRuns(page = 1, pageSize = 10, status = null, search = null) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status && status !== 'ALL') {
    params.append('status', status);
  }
  if (search && search.trim()) {
    params.append('search', search.trim());
  }

  const response = await fetch(`${API_BASE_URL}/workflows?${params.toString()}`, {
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

/**
 * Upload a document (PDF, TXT, MD) to the knowledge base for FAISS indexing.
 * @param {File} file
 * @returns {Promise<{ document_id: string, filename: string, status: string, page_count: number, chunk_count: number }>}
 */
export async function uploadDocument(file) {
  if (!file) throw new Error('File is required');

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const errorMsg = data?.detail || `Upload failed with HTTP ${response.status}`;
    throw new Error(errorMsg);
  }

  return data;
}

/**
 * Fetch paginated list of ingested documents.
 * @param {number} page
 * @param {number} pageSize
 * @returns {Promise<{ items: Array, total: number, page: number, page_size: number }>}
 */
export async function fetchDocuments(page = 1, pageSize = 20) {
  const response = await fetch(`${API_BASE_URL}/documents?page=${page}&page_size=${pageSize}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch documents (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Delete a document and its indexed vectors.
 * @param {string} documentId
 * @returns {Promise<{ status: string, document_id: string }>}
 */
export async function deleteDocument(documentId) {
  if (!documentId) throw new Error('documentId is required');

  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: 'DELETE',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete document (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch all workflow runs currently suspended waiting for human approval.
 * @returns {Promise<{ items: Array, total: number }>}
 */
export async function fetchPendingApprovals() {
  const response = await fetch(`${API_BASE_URL}/approvals/pending`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch pending approvals (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch approval details, latest candidate state, and revision history for a workflow run.
 * @param {string} runId
 * @returns {Promise<Object>}
 */
export async function fetchWorkflowApproval(runId) {
  if (!runId) throw new Error('runId is required');

  const response = await fetch(`${API_BASE_URL}/workflows/${runId}/approval`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch approval details (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Submit a human decision (APPROVE, REJECT, CHANGES_REQUESTED) to resume a suspended workflow.
 * @param {string} runId
 * @param {{ decision: string, feedback?: string, decided_by?: string }} payload
 * @returns {Promise<Object>}
 */
export async function submitApprovalDecision(runId, { decision, feedback, decided_by = 'human_reviewer' }) {
  if (!runId) throw new Error('runId is required');
  if (!decision) throw new Error('decision is required (APPROVE, REJECT, CHANGES_REQUESTED)');

  const response = await fetch(`${API_BASE_URL}/workflows/${runId}/approval`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      decision,
      feedback: feedback || '',
      decided_by,
    }),
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const errorMsg = data?.detail || `Failed to submit approval decision (HTTP ${response.status})`;
    throw new Error(errorMsg);
  }

  return data;
}

