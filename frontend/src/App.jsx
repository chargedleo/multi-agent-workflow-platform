import React, { useState, useEffect, useCallback } from 'react';
import { QueryInput } from './components/QueryInput';
import { WorkflowResult } from './components/WorkflowResult';
import { WorkflowHistory } from './components/WorkflowHistory';
import { RunDetailModal } from './components/RunDetailModal';
import { fetchHealth, executeWorkflow, fetchWorkflowRuns, fetchWorkflowRunDetail } from './services/api';
import './App.css';

export function App() {
  const [query, setQuery] = useState('Compare the advantages and disadvantages of PostgreSQL and MongoDB for a startup SaaS application.');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [healthInfo, setHealthInfo] = useState({ status: 'checking', database: 'unknown' });

  // History and inspection state
  const [runs, setRuns] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [selectedRunDetail, setSelectedRunDetail] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  // Load recent workflow runs
  const loadRuns = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const data = await fetchWorkflowRuns(1, 10);
      setRuns(data.items || []);
    } catch (err) {
      console.warn('Failed to load workflow runs:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Inspect run details
  const handleSelectRun = async (runId) => {
    setIsDetailLoading(true);
    try {
      const detail = await fetchWorkflowRunDetail(runId);
      setSelectedRunDetail(detail);
    } catch (err) {
      setError(`Failed to load details for run ${runId}: ${err.message}`);
    } finally {
      setIsDetailLoading(false);
    }
  };

  // Initial health check and runs load
  useEffect(() => {
    let isMounted = true;
    async function checkBackend() {
      try {
        const data = await fetchHealth();
        if (isMounted) {
          setHealthInfo(data);
        }
      } catch (err) {
        if (isMounted) {
          setHealthInfo({ status: 'offline', database: 'unreachable' });
        }
      }
    }
    checkBackend();
    loadRuns();
    const interval = setInterval(checkBackend, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [loadRuns]);

  const handleRunWorkflow = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await executeWorkflow(query);
      setResult(data);
      // Refresh run history to include the new run
      await loadRuns();
    } catch (err) {
      setError(err.message || 'An error occurred while executing the workflow.');
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-top">
          <div className="header-title-group">
            <div className="logo-badge">M</div>
            <h1 className="header-title">Multi-Agent AI Workflow Automation</h1>
          </div>
          <div className="header-badges">
            <span className="badge badge-milestone">Milestone 2 • PostgreSQL Persistence</span>
            <span className={`badge badge-status ${healthInfo.status !== 'healthy' ? 'disconnected' : ''}`}>
              <span className="status-dot"></span>
              API: {healthInfo.status}
            </span>
          </div>
        </div>
        <p className="header-subtitle">
          Autonomous multi-agent orchestration built with LangGraph, FastAPI, and PostgreSQL persistence.
          Specialized agents collaborate through shared state to plan, research, and synthesize structured results, with durable lifecycle tracking.
        </p>
      </header>

      {/* Agent Pipeline Visualizer */}
      <div className="pipeline-bar">
        <div className={`pipeline-node ${isLoading ? 'active' : result ? 'completed' : ''}`}>
          <span className="pipeline-icon">📋</span>
          <span>Planner Agent</span>
        </div>
        <span className="pipeline-arrow">→</span>
        <div className={`pipeline-node ${isLoading ? 'active' : result ? 'completed' : ''}`}>
          <span className="pipeline-icon">🔍</span>
          <span>Research Agent</span>
        </div>
        <span className="pipeline-arrow">→</span>
        <div className={`pipeline-node ${isLoading ? 'active' : result ? 'completed' : ''}`}>
          <span className="pipeline-icon">✨</span>
          <span>Response Agent</span>
        </div>
        <span className="pipeline-arrow">→</span>
        <div className={`pipeline-node ${result ? 'completed' : ''}`}>
          <span className="pipeline-icon">📊</span>
          <span>Structured Output</span>
        </div>
      </div>

      {/* Query Input Card */}
      <QueryInput
        query={query}
        setQuery={setQuery}
        onSubmit={handleRunWorkflow}
        isLoading={isLoading}
      />

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Workflow Result */}
      <WorkflowResult result={result} />

      {/* Persistent History Table */}
      <WorkflowHistory
        runs={runs}
        isLoading={isLoadingHistory}
        onSelectRun={handleSelectRun}
        onRefresh={loadRuns}
      />

      {/* Run Detail Modal */}
      {selectedRunDetail && (
        <RunDetailModal
          run={selectedRunDetail}
          onClose={() => setSelectedRunDetail(null)}
        />
      )}

      {/* Loading overlay for run detail */}
      {isDetailLoading && (
        <div className="loading-toast">Loading run details...</div>
      )}

      {/* Footer */}
      <footer className="app-footer">
        Portfolio Platform Architecture — Milestone 2: PostgreSQL Persistence & Workflow Run History
      </footer>
    </div>
  );
}

export default App;
