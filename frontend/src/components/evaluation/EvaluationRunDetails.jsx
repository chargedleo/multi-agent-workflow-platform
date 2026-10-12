import React, { useState, useEffect, useCallback } from 'react';
import { fetchEvaluationCaseResults, fetchEvaluationReport } from '../../services/api';

/**
 * Detailed view of an individual evaluation run with macro metrics,
 * category breakdowns, and expandable per-case diagnostic results.
 */
export function EvaluationRunDetails({
  run,
  onCompareRequest,
  onViewReportRequest,
  onBackToHistory,
}) {
  const [caseResults, setCaseResults] = useState([]);
  const [totalCases, setTotalCases] = useState(0);
  const [casePage, setCasePage] = useState(1);
  const [casePageSize, setCasePageSize] = useState(25);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [isLoadingCases, setIsLoadingCases] = useState(false);
  const [expandedCaseId, setExpandedCaseId] = useState(null);
  const [isDownloadingReport, setIsDownloadingReport] = useState(false);

  // Load per-case results
  const loadCaseResults = useCallback(async () => {
    if (!run?.id) return;
    setIsLoadingCases(true);
    try {
      const data = await fetchEvaluationCaseResults(
        run.id,
        categoryFilter || null,
        casePage,
        casePageSize
      );
      setCaseResults(data.items || []);
      setTotalCases(data.total || 0);
    } catch (err) {
      console.error('Failed to load case results:', err);
    } finally {
      setIsLoadingCases(false);
    }
  }, [run?.id, categoryFilter, casePage, casePageSize]);

  useEffect(() => {
    loadCaseResults();
  }, [loadCaseResults]);

  // Handle report file download
  const handleDownloadReport = async () => {
    if (!run?.id) return;
    setIsDownloadingReport(true);
    try {
      const reportData = await fetchEvaluationReport(run.id);
      const blob = new Blob([JSON.stringify(reportData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `evaluation_report_${run.id.slice(0, 8)}_${run.dataset_name}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Could not download report: ${err.message}`);
    } finally {
      setIsDownloadingReport(false);
    }
  };

  if (!run) {
    return (
      <div className="eval-panel">
        <div className="eval-empty">
          <p>No evaluation run selected. Choose a run from history.</p>
          <button className="eval-btn eval-btn-secondary" onClick={onBackToHistory}>
            View Run History
          </button>
        </div>
      </div>
    );
  }

  const summary = run.summary || run.aggregate_metrics || {};

  // Formatter helpers
  const fmtPct = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return `${(Number(val) * 100).toFixed(1)}%`;
  };

  const fmtDec = (val, digits = 4) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return Number(val).toFixed(digits);
  };

  return (
    <div className="eval-console-container">
      {/* Top Header Card */}
      <div className="eval-panel">
        <div className="eval-panel-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <span className="eval-panel-title">
                Run Details: <span className="eval-mono">{run.id.slice(0, 8)}...</span>
              </span>
              <span className={`eval-badge eval-badge-status-${(run.status || '').toLowerCase()}`}>
                {run.status}
              </span>
              <span className="eval-badge eval-badge-mode">{run.mode}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
              Dataset: <strong>{run.dataset_name}</strong> (v{run.dataset_version}) •
              Duration: <strong>{run.duration_ms ? `${run.duration_ms.toFixed(1)}ms` : '—'}</strong> •
              Created: {run.created_at ? new Date(run.created_at).toLocaleString() : '—'}
            </div>
          </div>

          <div className="eval-panel-actions">
            <button
              className="eval-btn eval-btn-secondary eval-btn-sm"
              onClick={onBackToHistory}
            >
              Back to History
            </button>
            <button
              className="eval-btn eval-btn-secondary eval-btn-sm"
              onClick={() => onCompareRequest && onCompareRequest(run)}
            >
              Compare Run
            </button>
            <button
              className="eval-btn eval-btn-secondary eval-btn-sm"
              onClick={() => onViewReportRequest && onViewReportRequest(run)}
            >
              View Raw JSON
            </button>
            <button
              className="eval-btn eval-btn-sm"
              onClick={handleDownloadReport}
              disabled={isDownloadingReport}
            >
              {isDownloadingReport ? 'Downloading...' : 'Download Report'}
            </button>
          </div>
        </div>

        {/* Checksum & Config bar */}
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
          <span>SHA256: <code className="eval-mono">{run.dataset_checksum ? run.dataset_checksum.slice(0, 16) + '...' : '—'}</code></span>
          <span>App Version: {run.application_version || '0.1.0'}</span>
          <span>Cases Evaluated: {summary.completed_cases ?? '—'} / {summary.total_cases ?? '—'}</span>
        </div>
      </div>

      {/* Aggregate Metric Groups */}
      <div className="eval-panel">
        <div className="eval-panel-title">
          Deterministic Performance Summary
        </div>

        {/* 1. Retrieval Metrics */}
        <div>
          <h4 style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            1. FAISS Retrieval Performance
          </h4>
          <div className="eval-stats-grid">
            <div className="eval-stat-card">
              <span className="eval-stat-title">Mean Recall@1</span>
              <span className="eval-stat-value">{fmtPct(summary.mean_recall_at_1)}</span>
              <span className="eval-stat-subtext">Recall@3: {fmtPct(summary.mean_recall_at_3)} • Recall@5: {fmtPct(summary.mean_recall_at_5)}</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Mean Precision@1</span>
              <span className="eval-stat-value">{fmtPct(summary.mean_precision_at_1)}</span>
              <span className="eval-stat-subtext">Precision@3: {fmtPct(summary.mean_precision_at_3)} • Precision@5: {fmtPct(summary.mean_precision_at_5)}</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">MRR (Mean Reciprocal Rank)</span>
              <span className="eval-stat-value">{fmtDec(summary.mrr, 4)}</span>
              <span className="eval-stat-subtext">1 / rank of first relevant chunk</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">MAP Score</span>
              <span className="eval-stat-value">{fmtDec(summary.map_score, 4)}</span>
              <span className="eval-stat-subtext">Mean Average Precision</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Hit Rate@1</span>
              <span className="eval-stat-value">{fmtPct(summary.mean_hit_rate_at_1)}</span>
              <span className="eval-stat-subtext">Avg latency: {summary.avg_retrieval_latency_ms ? `${summary.avg_retrieval_latency_ms.toFixed(1)}ms` : '—'}</span>
            </div>
          </div>
        </div>

        {/* 2. Citation & Answer Quality */}
        <div style={{ marginTop: '0.75rem' }}>
          <h4 style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            2. Citation Integrity & Answer Provenance
          </h4>
          <div className="eval-stats-grid">
            <div className="eval-stat-card">
              <span className="eval-stat-title">Citation Presence Rate</span>
              <span className="eval-stat-value">{fmtPct(summary.citation_presence_rate)}</span>
              <span className="eval-stat-subtext">Attribution Match: {fmtPct(summary.attribution_match_rate)}</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Identifier Validity</span>
              <span className="eval-stat-value">{fmtPct(summary.identifier_validity_rate)}</span>
              <span className="eval-stat-subtext">Source Validity: {fmtPct(summary.source_validity_rate)}</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Mean Fact Coverage</span>
              <span className="eval-stat-value">{fmtPct(summary.mean_fact_coverage)}</span>
              <span className="eval-stat-subtext">Ground truth atomic facts matched</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Abstention Accuracy</span>
              <span className="eval-stat-value">{fmtPct(summary.abstention_accuracy)}</span>
              <span className="eval-stat-subtext">Unanswerable queries correctly rejected</span>
            </div>
            <div className="eval-stat-card">
              <span className="eval-stat-title">Guardrail Accuracy</span>
              <span className="eval-stat-value">{fmtPct(summary.guardrail_accuracy)}</span>
              <span className="eval-stat-subtext">FPR: {fmtPct(summary.false_positive_rate)} • FNR: {fmtPct(summary.false_negative_rate)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Paginated Per-Case Results Table */}
      <div className="eval-panel">
        <div className="eval-panel-header">
          <div className="eval-panel-title">
            Benchmark Case Diagnostics ({totalCases} Cases)
          </div>
          <div className="eval-panel-actions">
            <select
              className="eval-form-select"
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setCasePage(1);
              }}
            >
              <option value="">All Categories</option>
              <option value="answerable">answerable</option>
              <option value="multi_hop">multi_hop</option>
              <option value="unanswerable">unanswerable</option>
              <option value="ambiguous">ambiguous</option>
              <option value="citation_sensitive">citation_sensitive</option>
              <option value="unsupported_premise">unsupported_premise</option>
              <option value="retrieval_edge_case">retrieval_edge_case</option>
            </select>
          </div>
        </div>

        {isLoadingCases ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            <span className="eval-active-spinner"></span> Loading case evaluations...
          </div>
        ) : caseResults.length === 0 ? (
          <div className="eval-empty">
            <p>No case results found for the selected category filter.</p>
          </div>
        ) : (
          <div className="eval-table-container">
            <table className="eval-table">
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Recall@1</th>
                  <th>Precision@1</th>
                  <th>Fact Match</th>
                  <th>Guardrail</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {caseResults.map((c) => {
                  const m = c.metric_results || {};
                  const ret = m.retrieval || {};
                  const ans = m.answer || {};
                  const grd = m.guardrail || {};
                  const isExpanded = expandedCaseId === c.id;

                  return (
                    <React.Fragment key={c.id}>
                      <tr>
                        <td className="eval-mono" style={{ fontWeight: 600 }}>{c.case_id}</td>
                        <td>
                          <span className="eval-badge eval-badge-category">{c.category}</span>
                        </td>
                        <td>
                          <span className={`eval-badge eval-badge-status-${(c.status || '').toLowerCase()}`}>
                            {c.status}
                          </span>
                        </td>
                        <td className="eval-mono">{c.duration_ms ? `${c.duration_ms.toFixed(1)}ms` : '—'}</td>
                        <td className="eval-mono">{fmtPct(ret.recall_at_1)}</td>
                        <td className="eval-mono">{fmtPct(ret.precision_at_1)}</td>
                        <td className="eval-mono">{fmtPct(ans.fact_coverage)}</td>
                        <td>
                          <span
                            className={`eval-badge ${grd.status_match ? 'eval-badge-status-completed' : 'eval-badge-status-failed'}`}
                          >
                            {grd.actual_status || '—'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="eval-btn eval-btn-secondary eval-btn-sm"
                            onClick={() => setExpandedCaseId(isExpanded ? null : c.id)}
                          >
                            {isExpanded ? 'Hide' : 'Inspect'}
                          </button>
                        </td>
                      </tr>

                      {/* Expandable Case Detail Panel */}
                      {isExpanded && (
                        <tr>
                          <td colSpan="9" style={{ padding: 0 }}>
                            <div className="eval-case-expandable">
                              {/* Retrieval Metrics Pills */}
                              <div className="eval-case-detail-block">
                                <span className="eval-case-detail-label">Detailed Metric Breakdown</span>
                                <div className="eval-metrics-pill-row">
                                  <div className="eval-pill">
                                    <span className="eval-pill-label">MRR:</span>
                                    <span className="eval-pill-val">{fmtDec(ret.mrr, 2)}</span>
                                  </div>
                                  <div className="eval-pill">
                                    <span className="eval-pill-label">HitRate@1:</span>
                                    <span className="eval-pill-val">{fmtPct(ret.hit_rate_at_1)}</span>
                                  </div>
                                  <div className="eval-pill">
                                    <span className="eval-pill-label">Retrieved Chunks:</span>
                                    <span className="eval-pill-val">{ret.retrieved_count ?? 0}</span>
                                  </div>
                                  <div className="eval-pill">
                                    <span className="eval-pill-label">Relevant Ground Truth:</span>
                                    <span className="eval-pill-val">{ret.relevant_count ?? 0}</span>
                                  </div>
                                  {ans.correct_abstention !== null && ans.correct_abstention !== undefined && (
                                    <div className="eval-pill">
                                      <span className="eval-pill-label">Abstention Verdict:</span>
                                      <span className="eval-pill-val">
                                        {ans.correct_abstention ? 'Valid Abstention' : 'Hallucination'}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Facts Matched / Missing */}
                              {ans.matched_facts && ans.matched_facts.length > 0 && (
                                <div className="eval-case-detail-block">
                                  <span className="eval-case-detail-label" style={{ color: 'var(--success)' }}>
                                    Matched Ground-Truth Facts ({ans.matched_facts.length})
                                  </span>
                                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    {ans.matched_facts.map((f, idx) => (
                                      <li key={idx}>{f}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {ans.missing_facts && ans.missing_facts.length > 0 && (
                                <div className="eval-case-detail-block">
                                  <span className="eval-case-detail-label" style={{ color: 'var(--danger)' }}>
                                    Missing Expected Facts ({ans.missing_facts.length})
                                  </span>
                                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    {ans.missing_facts.map((f, idx) => (
                                      <li key={idx}>{f}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {/* Safe Error Details */}
                              {c.safe_error_summary && (
                                <div className="eval-case-detail-block">
                                  <span className="eval-case-detail-label" style={{ color: 'var(--danger)' }}>
                                    Execution Error Summary
                                  </span>
                                  <span style={{ fontSize: '0.8rem', color: 'var(--danger)' }}>
                                    {c.safe_error_summary}
                                  </span>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {totalCases > casePageSize && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Showing {caseResults.length} of {totalCases} cases (Page {casePage} of {Math.ceil(totalCases / casePageSize)})
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className="eval-btn eval-btn-secondary eval-btn-sm"
                disabled={casePage <= 1}
                onClick={() => setCasePage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <button
                className="eval-btn eval-btn-secondary eval-btn-sm"
                disabled={casePage >= Math.ceil(totalCases / casePageSize)}
                onClick={() => setCasePage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
