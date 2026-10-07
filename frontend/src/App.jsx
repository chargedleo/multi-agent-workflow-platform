import React, { useState, useEffect } from 'react';
import { QueryInput } from './components/QueryInput';
import { WorkflowResult } from './components/WorkflowResult';
import { fetchHealth, executeWorkflow } from './services/api';
import './App.css';

export function App() {
  const [query, setQuery] = useState('Compare the advantages and disadvantages of PostgreSQL and MongoDB for a startup SaaS application.');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [healthInfo, setHealthInfo] = useState({ status: 'checking', database: 'unknown' });

  // Initial health check
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
    const interval = setInterval(checkBackend, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRunWorkflow = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await executeWorkflow(query);
      setResult(data);
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
            <span className="badge badge-milestone">Milestone 1</span>
            <span className={`badge badge-status ${healthInfo.status !== 'healthy' ? 'disconnected' : ''}`}>
              <span className="status-dot"></span>
              API: {healthInfo.status}
            </span>
          </div>
        </div>
        <p className="header-subtitle">
          Autonomous multi-agent orchestration built with LangGraph, FastAPI, and Pydantic.
          Specialized agents collaborate through shared state to plan, research, and deliver structured insights.
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

      {/* Footer */}
      <footer className="app-footer">
        Portfolio Platform Architecture — Milestone 1: Project Foundation & Core Agent Workflow
      </footer>
    </div>
  );
}

export default App;
