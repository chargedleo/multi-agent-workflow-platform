import React, { useState, useEffect } from 'react';
import { compareEvaluations } from '../../services/api';

/**
 * Compare two evaluation runs to calculate metric deltas, regressions, and improvements.
 */
export function EvaluationCompareView({ runs, initialBaselineRun, initialComparisonRun }) {
  const completedRuns = (runs || []).filter((r) => r.status === 'COMPLETED');

  const [baselineRunId, setBaselineRunId] = useState(
    initialBaselineRun?.id || (completedRuns[1]?.id || completedRuns[0]?.id || '')
  );
  const [comparisonRunId, setComparisonRunId] = useState(
    initialComparisonRun?.id || (completedRuns[0]?.id || '')
  );

  const [comparisonReport, setComparisonReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Sync initial props
  useEffect(() => {
    if (initialBaselineRun?.id) setBaselineRunId(initialBaselineRun.id);
  }, [initialBaselineRun]);

  useEffect(() => {
    if (initialComparisonRun?.id) setComparisonRunId(initialComparisonRun.id);
  }, [initialComparisonRun]);

  const handleRunComparison = async () => {
    if (!baselineRunId || !comparisonRunId) return;
    if (baselineRunId === comparisonRunId) {
      setError('Please select two distinct evaluation runs to compare.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const report = await compareEvaluations(baselineRunId, comparisonRunId);
      setComparisonReport(report);
    } catch (err) {
      setError(err.message || 'Failed to compare evaluation runs');
      setComparisonReport(null);
    } finally {
      setIsLoading(false);
    }
  };

  const fmtVal = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return Number(val).toFixed(4);
  };

  const fmtDelta = (delta) => {
    if (delta === null || delta === undefined || isNaN(delta)) return '—';
    const num = Number(delta);
    const sign = num > 0 ? '+' : '';
    return `${sign}${num.toFixed(4)}`;
  };

  const getVerdictClass = (verdict) => {
    const v = (verdict || '').toUpperCase();
    if (v === 'IMPROVED') return 'improved';
    if (v === 'REGRESSED') return 'regressed';
    return 'neutral';
  };

  return (
    <div className="eval-console-container">
      {/* Selector Panel */}
      <div className="eval-panel">
        <div className="eval-panel-header">
          <div className="eval-panel-title">
            Compare Benchmark Evaluation Runs
          </div>
        </div>

        <div className="eval-compare-header">
          {/* Baseline Run */}
          <div className="eval-form-group">
            <label className="eval-form-label" htmlFor="eval-baseline-select">
              Baseline Run (Reference)
            </label>
            <select
              id="eval-baseline-select"
              className="eval-form-select"
              value={baselineRunId}
              onChange={(e) => setBaselineRunId(e.target.value)}
            >
              <option value="">Select Baseline Run...</option>
              {completedRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id.slice(0, 8)}... ({r.dataset_name} • {r.mode} • {new Date(r.created_at).toLocaleTimeString()})
                </option>
              ))}
            </select>
          </div>

          {/* Target Comparison Run */}
          <div className="eval-form-group">
            <label className="eval-form-label" htmlFor="eval-comparison-select">
              Comparison Run (Target)
            </label>
            <select
              id="eval-comparison-select"
              className="eval-form-select"
              value={comparisonRunId}
              onChange={(e) => setComparisonRunId(e.target.value)}
            >
              <option value="">Select Target Run...</option>
              {completedRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id.slice(0, 8)}... ({r.dataset_name} • {r.mode} • {new Date(r.created_at).toLocaleTimeString()})
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="error-banner">
            <strong>Comparison Error:</strong> {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="eval-btn"
            onClick={handleRunComparison}
            disabled={isLoading || !baselineRunId || !comparisonRunId}
          >
            {isLoading ? (
              <>
                <span className="eval-active-spinner"></span>
                <span>Calculating Metric Deltas...</span>
              </>
            ) : (
              <span>Compare Selected Runs</span>
            )}
          </button>
        </div>
      </div>

      {/* Comparison Results */}
      {comparisonReport && (
        <div className="eval-panel">
          {/* Verdict Banner */}
          <div className={`eval-verdict-banner ${getVerdictClass(comparisonReport.summary_verdict)}`}>
            <div>
              <span>Overall Verdict: <strong>{comparisonReport.summary_verdict}</strong></span>
            </div>
            <div style={{ fontSize: '0.8rem' }}>
              Baseline: <span className="eval-mono">{comparisonReport.baseline_run_id.slice(0, 8)}</span> ({comparisonReport.baseline_mode}) vs{' '}
              Target: <span className="eval-mono">{comparisonReport.comparison_run_id.slice(0, 8)}</span> ({comparisonReport.comparison_mode})
            </div>
          </div>

          {/* Regressions Alert */}
          {comparisonReport.regressions && comparisonReport.regressions.length > 0 && (
            <div className="error-banner" style={{ marginTop: '0.5rem' }}>
              <strong>Detected Metric Regressions ({comparisonReport.regressions.length}):</strong>
              <ul style={{ paddingLeft: '1.25rem', marginTop: '0.25rem' }}>
                {comparisonReport.regressions.map((reg, idx) => (
                  <li key={idx}>{reg}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Improvements Notice */}
          {comparisonReport.improvements && comparisonReport.improvements.length > 0 && (
            <div style={{ background: 'var(--success-bg)', border: '1px solid rgba(16, 185, 129, 0.4)', color: 'var(--success)', padding: '0.85rem 1.25rem', borderRadius: 'var(--radius-sm)' }}>
              <strong>Metric Improvements ({comparisonReport.improvements.length}):</strong>
              <ul style={{ paddingLeft: '1.25rem', marginTop: '0.25rem' }}>
                {comparisonReport.improvements.map((imp, idx) => (
                  <li key={idx}>{imp}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Metric Deltas Table */}
          <div className="eval-table-container">
            <table className="eval-table">
              <thead>
                <tr>
                  <th>Metric Name</th>
                  <th>Baseline Value</th>
                  <th>Target Value</th>
                  <th>Delta (Target - Baseline)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(comparisonReport.metric_deltas || {}).map(([metricName, deltaObj]) => {
                  const statusClass =
                    deltaObj.status === 'IMPROVED'
                      ? 'eval-badge-delta-improved'
                      : deltaObj.status === 'REGRESSED'
                      ? 'eval-badge-delta-regressed'
                      : 'eval-badge-delta-unchanged';

                  return (
                    <tr key={metricName}>
                      <td style={{ fontWeight: 600 }}>{metricName.replace(/_/g, ' ')}</td>
                      <td className="eval-mono">{fmtVal(deltaObj.baseline)}</td>
                      <td className="eval-mono">{fmtVal(deltaObj.comparison)}</td>
                      <td className="eval-mono" style={{ fontWeight: 700 }}>
                        {fmtDelta(deltaObj.delta)}
                      </td>
                      <td>
                        <span className={`eval-badge ${statusClass}`}>{deltaObj.status}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
