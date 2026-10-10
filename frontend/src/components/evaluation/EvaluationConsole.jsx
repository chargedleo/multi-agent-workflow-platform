import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  fetchEvaluationRuns,
  fetchEvaluationRun,
  fetchEvaluationReport,
} from '../../services/api';
import { EvaluationLaunchForm } from './EvaluationLaunchForm';
import { EvaluationRunDetails } from './EvaluationRunDetails';
import { EvaluationCompareView } from './EvaluationCompareView';
import './EvaluationConsole.css';

/**
 * Root Evaluation Console View (Milestone 9B).
 * Provides benchmarking overview, execution launch, run history,
 * metric inspection, per-case diagnostics, run comparison, and JSON report export.
 */
export function EvaluationConsole() {
  // Sub-tabs: 'overview', 'history', 'details', 'compare', 'report'
  const [activeTab, setActiveTab] = useState('overview');

  // Runs List & Pagination
  const [runs, setRuns] = useState([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);

  // Active / Selected Run State
  const [selectedRun, setSelectedRun] = useState(null);
  const [activeRunningRun, setActiveRunningRun] = useState(null);

  // Compare targets state
  const [compareBaseline, setCompareBaseline] = useState(null);
  const [compareTarget, setCompareTarget] = useState(null);

  // JSON Report Viewer State
  const [reportData, setReportData] = useState(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);

  // Polling ref
  const pollTimerRef = useRef(null);

  // 1. Fetch Runs
  const loadRuns = useCallback(async (p = page, ps = pageSize) => {
    setIsLoadingRuns(true);
    try {
      const data = await fetchEvaluationRuns(p, ps);
      setRuns(data.items || []);
      setTotalRuns(data.total || 0);

      // Check if any run is currently running/pending
      const inFlight = (data.items || []).find(
        (r) => r.status === 'RUNNING' || r.status === 'PENDING'
      );
      if (inFlight) {
        setActiveRunningRun(inFlight);
      }
    } catch (err) {
      console.warn('Failed to load evaluation runs:', err);
    } finally {
      setIsLoadingRuns(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    loadRuns(page, pageSize);
  }, [loadRuns, page, pageSize]);

  // 2. Active Run Polling
  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (activeRunningRun && (activeRunningRun.status === 'RUNNING' || activeRunningRun.status === 'PENDING')) {
      pollTimerRef.current = setInterval(async () => {
        try {
          const fresh = await fetchEvaluationRun(activeRunningRun.id);
          if (fresh.status === 'COMPLETED' || fresh.status === 'FAILED') {
            setActiveRunningRun(null);
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
            // Reload all runs and update selectedRun
            await loadRuns(page, pageSize);
            setSelectedRun(fresh);
          } else {
            setActiveRunningRun(fresh);
          }
        } catch (err) {
          console.error('Error polling evaluation run:', err);
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      }, 2000);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [activeRunningRun, loadRuns, page, pageSize]);

  // Handle run created from launch form
  const handleRunStarted = (newRun) => {
    setActiveRunningRun(newRun);
    loadRuns(1, pageSize);
  };

  // Inspect run details
  const handleSelectRun = async (runId) => {
    try {
      const detail = await fetchEvaluationRun(runId);
      setSelectedRun(detail);
      setActiveTab('details');
    } catch (err) {
      alert(`Could not load details for run ${runId}: ${err.message}`);
    }
  };

  // View JSON report
  const handleViewReport = async (run) => {
    if (!run?.id) return;
    setIsLoadingReport(true);
    try {
      const rep = await fetchEvaluationReport(run.id);
      setReportData(rep);
      setSelectedRun(run);
      setActiveTab('report');
    } catch (err) {
      alert(`Could not load report: ${err.message}`);
    } finally {
      setIsLoadingReport(false);
    }
  };

  // Prepare comparison
  const handleInitiateCompare = (run) => {
    setCompareTarget(run);
    setActiveTab('compare');
  };

  // Quick stats calculation
  const completedCount = runs.filter((r) => r.status === 'COMPLETED').length;
  const runningCount = runs.filter((r) => r.status === 'RUNNING' || r.status === 'PENDING').length;
  const failedCount = runs.filter((r) => r.status === 'FAILED').length;
  const latestRun = runs[0] || null;

  return (
    <div className="eval-console-container">
      {/* Sub-Navigation Header */}
      <nav className="eval-subnav">
        <button
          className={`eval-subnav-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <span>🚀</span> Overview & Launch
        </button>
        <button
          className={`eval-subnav-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <span>📋</span> Evaluation History ({totalRuns})
        </button>
        <button
          className={`eval-subnav-btn ${activeTab === 'details' ? 'active' : ''}`}
          onClick={() => setActiveTab('details')}
          disabled={!selectedRun}
        >
          <span>📊</span> Run Details {selectedRun ? `(${selectedRun.id.slice(0, 6)}...)` : ''}
        </button>
        <button
          className={`eval-subnav-btn ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
        >
          <span>⚖️</span> Compare Runs
        </button>
        <button
          className={`eval-subnav-btn ${activeTab === 'report' ? 'active' : ''}`}
          onClick={() => setActiveTab('report')}
          disabled={!reportData && !selectedRun}
        >
          <span>📄</span> JSON Report
        </button>
      </nav>

      {/* Active Polling Banner */}
      {activeRunningRun && (
        <div className="eval-active-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="eval-active-spinner"></span>
            <div>
              <strong>Evaluation in Progress:</strong> Run{' '}
              <span className="eval-mono">{activeRunningRun.id.slice(0, 8)}...</span> (
              {activeRunningRun.dataset_name} • {activeRunningRun.mode})
            </div>
          </div>
          <span className="eval-badge eval-badge-status-running">
            {activeRunningRun.status}
          </span>
        </div>
      )}

      {/* TAB 1: OVERVIEW & LAUNCH */}
      {activeTab === 'overview' && (
        <>
          {/* Macro Stats Grid */}
          <div className="eval-stats-grid">
            <div className="eval-stat-card">
              <span className="eval-stat-title">Total Benchmark Runs</span>
              <span className="eval-stat-value">{totalRuns}</span>
              <span className="eval-stat-subtext">Persisted in PostgreSQL</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Completed Runs</span>
              <span className="eval-stat-value" style={{ color: 'var(--success)' }}>
                {completedCount}
              </span>
              <span className="eval-stat-subtext">Deterministic & Verified</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">In-Flight / Running</span>
              <span className="eval-stat-value" style={{ color: '#818cf8' }}>
                {runningCount}
              </span>
              <span className="eval-stat-subtext">Active background workers</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Failed Runs</span>
              <span className="eval-stat-value" style={{ color: failedCount > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                {failedCount}
              </span>
              <span className="eval-stat-subtext">Execution exceptions</span>
            </div>
          </div>

          {/* Launch Form */}
          <EvaluationLaunchForm
            onRunStarted={handleRunStarted}
            activeRunningRun={activeRunningRun}
          />

          {/* Recent Runs Quick View */}
          {runs.length > 0 && (
            <div className="eval-panel">
              <div className="eval-panel-header">
                <div className="eval-panel-title">
                  <span>🕒</span> Most Recent Evaluation Runs
                </div>
                <button
                  className="eval-btn eval-btn-secondary eval-btn-sm"
                  onClick={() => setActiveTab('history')}
                >
                  View All ({totalRuns}) →
                </button>
              </div>

              <div className="eval-table-container">
                <table className="eval-table">
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Dataset</th>
                      <th>Mode</th>
                      <th>Status</th>
                      <th>Recall@1</th>
                      <th>Precision@1</th>
                      <th>MRR</th>
                      <th>Duration</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.slice(0, 5).map((r) => {
                      const sum = r.summary || r.aggregate_metrics || {};
                      return (
                        <tr key={r.id}>
                          <td className="eval-mono" style={{ fontWeight: 600 }}>{r.id.slice(0, 8)}...</td>
                          <td>{r.dataset_name}</td>
                          <td><span className="eval-badge eval-badge-mode">{r.mode}</span></td>
                          <td>
                            <span className={`eval-badge eval-badge-status-${(r.status || '').toLowerCase()}`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="eval-mono">{sum.mean_recall_at_1 ? `${(sum.mean_recall_at_1 * 100).toFixed(1)}%` : '—'}</td>
                          <td className="eval-mono">{sum.mean_precision_at_1 ? `${(sum.mean_precision_at_1 * 100).toFixed(1)}%` : '—'}</td>
                          <td className="eval-mono">{sum.mrr ? Number(sum.mrr).toFixed(3) : '—'}</td>
                          <td className="eval-mono">{r.duration_ms ? `${r.duration_ms.toFixed(0)}ms` : '—'}</td>
                          <td>
                            <button
                              className="eval-btn eval-btn-secondary eval-btn-sm"
                              onClick={() => handleSelectRun(r.id)}
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* TAB 2: RUN HISTORY */}
      {activeTab === 'history' && (
        <div className="eval-panel">
          <div className="eval-panel-header">
            <div className="eval-panel-title">
              <span>📋</span> Complete Evaluation Run History
            </div>
            <button
              className="eval-btn eval-btn-secondary eval-btn-sm"
              onClick={() => loadRuns(page, pageSize)}
            >
              🔄 Refresh
            </button>
          </div>

          {isLoadingRuns ? (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-secondary)' }}>
              <span className="eval-active-spinner"></span> Loading evaluation history...
            </div>
          ) : runs.length === 0 ? (
            <div className="eval-empty">
              <span className="eval-empty-icon">📭</span>
              <p>No evaluation runs recorded yet.</p>
              <button className="eval-btn" onClick={() => setActiveTab('overview')}>
                Launch First Benchmark
              </button>
            </div>
          ) : (
            <>
              <div className="eval-table-container">
                <table className="eval-table">
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Dataset</th>
                      <th>Mode</th>
                      <th>Status</th>
                      <th>Started At</th>
                      <th>Duration</th>
                      <th>Recall@1</th>
                      <th>MRR</th>
                      <th>Guardrail Acc</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => {
                      const sum = r.summary || r.aggregate_metrics || {};
                      return (
                        <tr key={r.id}>
                          <td className="eval-mono" style={{ fontWeight: 600 }}>{r.id.slice(0, 8)}...</td>
                          <td>{r.dataset_name} (v{r.dataset_version})</td>
                          <td><span className="eval-badge eval-badge-mode">{r.mode}</span></td>
                          <td>
                            <span className={`eval-badge eval-badge-status-${(r.status || '').toLowerCase()}`}>
                              {r.status}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
                          </td>
                          <td className="eval-mono">{r.duration_ms ? `${r.duration_ms.toFixed(0)}ms` : '—'}</td>
                          <td className="eval-mono">{sum.mean_recall_at_1 ? `${(sum.mean_recall_at_1 * 100).toFixed(1)}%` : '—'}</td>
                          <td className="eval-mono">{sum.mrr ? Number(sum.mrr).toFixed(3) : '—'}</td>
                          <td className="eval-mono">{sum.guardrail_accuracy ? `${(sum.guardrail_accuracy * 100).toFixed(1)}%` : '—'}</td>
                          <td>
                            <div style={{ display: 'flex', gap: '0.35rem' }}>
                              <button
                                className="eval-btn eval-btn-secondary eval-btn-sm"
                                onClick={() => handleSelectRun(r.id)}
                              >
                                Details
                              </button>
                              <button
                                className="eval-btn eval-btn-secondary eval-btn-sm"
                                onClick={() => handleInitiateCompare(r)}
                              >
                                Compare
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalRuns > pageSize && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Showing {runs.length} of {totalRuns} runs (Page {page} of {Math.ceil(totalRuns / pageSize)})
                  </span>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className="eval-btn eval-btn-secondary eval-btn-sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </button>
                    <button
                      className="eval-btn eval-btn-secondary eval-btn-sm"
                      disabled={page >= Math.ceil(totalRuns / pageSize)}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* TAB 3: RUN DETAILS */}
      {activeTab === 'details' && selectedRun && (
        <EvaluationRunDetails
          run={selectedRun}
          onCompareRequest={handleInitiateCompare}
          onViewReportRequest={handleViewReport}
          onBackToHistory={() => setActiveTab('history')}
        />
      )}

      {/* TAB 4: COMPARE RUNS */}
      {activeTab === 'compare' && (
        <EvaluationCompareView
          runs={runs}
          initialBaselineRun={compareBaseline}
          initialComparisonRun={compareTarget || selectedRun}
        />
      )}

      {/* TAB 5: JSON REPORT VIEWER */}
      {activeTab === 'report' && (
        <div className="eval-panel">
          <div className="eval-panel-header">
            <div className="eval-panel-title">
              <span>📄</span> Standalone Evaluation JSON Report
            </div>
            {reportData && (
              <div className="eval-panel-actions">
                <button
                  className="eval-btn eval-btn-sm"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
                      type: 'application/json',
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `report_${reportData.evaluation_run_id}.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                >
                  ⬇ Download JSON Report
                </button>
              </div>
            )}
          </div>

          {isLoadingReport ? (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-secondary)' }}>
              <span className="eval-active-spinner"></span> Loading report...
            </div>
          ) : reportData ? (
            <pre className="eval-json-box">
              {JSON.stringify(reportData, null, 2)}
            </pre>
          ) : (
            <div className="eval-empty">
              <p>No report loaded. Select a completed run from history to view its report.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
