import React from 'react';
import { ApprovalCard } from './ApprovalCard';

export function WorkflowResult({ result, onApprovalDone }) {
  if (!result) return null;

  const { request_id, answer, key_points, confidence, sources, analysis_results, validation, errors } = result;
  const confidencePercent = Math.round((confidence || 0) * 100);

  return (
    <div className="result-card">
      <div className="result-header">
        <div className="result-title-group">
          <h2 className="result-title">Workflow Result</h2>
          {request_id && (
            <span className="req-badge" title="Unique Request ID">
              ID: {request_id}
            </span>
          )}
          {result.approval_status && (
            <span className={`status-badge status-${result.approval_status.toLowerCase()}`}>
              Approval: {result.approval_status}
            </span>
          )}
        </div>

        <div className="confidence-box">
          <span className="confidence-label">Confidence</span>
          <span className="confidence-val">{confidencePercent}%</span>
        </div>
      </div>

      {/* Human Approval Review Gate if currently suspended */}
      {(result.status === 'WAITING_FOR_APPROVAL' || result.approval_status === 'PENDING') && (
        <div style={{ marginBottom: '1.25rem' }}>
          <ApprovalCard
            runId={result.run_id}
            result={result}
            onDecisionSubmitted={onApprovalDone}
          />
        </div>
      )}

      {/* Human Rejection Notice if rejected */}
      {result.approval_status === 'REJECTED' && (
        <div className="error-banner" style={{ marginBottom: '1.25rem' }}>
          <div>
            <strong>Workflow Rejected by Human Reviewer:</strong> This execution was terminated at the review gate and not released to downstream services.
          </div>
        </div>
      )}

      {errors && errors.length > 0 && (
        <div className="error-banner">
          <div>
            <strong>Warnings / Non-fatal errors recorded:</strong>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.25rem' }}>
              {errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="answer-section">
        <div className="section-label">Synthesized Response</div>
        <div className="answer-body">{answer}</div>
      </div>

      {key_points && key_points.length > 0 && (
        <div className="key-points-section">
          <div className="section-label">Executive Key Points</div>
          <div className="key-points-grid">
            {key_points.map((point, idx) => (
              <div key={idx} className="key-point-item">
                <span className="key-point-bullet">•</span>
                <span>{point}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quantitative Data Analysis Section */}
      {analysis_results && analysis_results.status === 'completed' && (
        <div className="analysis-section">
          <div className="analysis-header">
            <div className="section-label" style={{ marginBottom: 0 }}>
              Quantitative Data Analysis (MCP Verified)
            </div>
            <div className="analysis-badges">
              <span className="badge badge-tech">
                Tool: {analysis_results.tool_name || 'analyze_dataset'}
              </span>
              <span className="badge badge-tech">
                Dataset: {analysis_results.dataset}
              </span>
              <span className="badge badge-tech">
                Op: {analysis_results.operation}
              </span>
              {analysis_results.execution_time_ms != null && (
                <span className="badge badge-tech">
                  {typeof analysis_results.execution_time_ms === 'number'
                    ? `${analysis_results.execution_time_ms.toFixed(1)} ms`
                    : `${analysis_results.execution_time_ms} ms`}
                </span>
              )}
            </div>
          </div>

          {analysis_results.summary && (
            <div className="analysis-summary-box">
              <span>{analysis_results.summary}</span>
            </div>
          )}

          {analysis_results.metrics && Object.keys(analysis_results.metrics).length > 0 && (
            <div className="analysis-metrics-grid">
              {Object.entries(analysis_results.metrics).map(([key, val]) => (
                <div key={key} className="analysis-metric-card">
                  <div className="analysis-metric-label">{key.replace(/_/g, ' ').toUpperCase()}</div>
                  <div className="analysis-metric-value">
                    {typeof val === 'number'
                      ? val.toLocaleString(undefined, { maximumFractionDigits: 2 })
                      : String(val)}
                  </div>
                </div>
              ))}
            </div>
          )}

          {analysis_results.rows && analysis_results.rows.length > 0 && (
            <div className="analysis-table-container">
              <table className="analysis-table">
                <thead>
                  <tr>
                    {(analysis_results.columns && analysis_results.columns.length > 0
                      ? analysis_results.columns
                      : Object.keys(analysis_results.rows[0])
                    ).map((col) => (
                      <th key={col}>{col.replace(/_/g, ' ')}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {analysis_results.rows.map((row, idx) => (
                    <tr key={idx}>
                      {(analysis_results.columns && analysis_results.columns.length > 0
                        ? analysis_results.columns
                        : Object.keys(row)
                      ).map((col) => (
                        <td key={col}>
                          {typeof row[col] === 'number'
                            ? row[col].toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : String(row[col] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {analysis_results && analysis_results.status === 'failed' && (
        <div className="error-banner" style={{ marginTop: '1rem' }}>
          <strong>Data Analysis Notice:</strong> {analysis_results.error || 'Structured data analysis failed.'}
        </div>
      )}

      {/* Validation Guardrails Section */}
      {validation && (
        <div className="validation-section">
          <div className="validation-header">
            <div className="section-label" style={{ marginBottom: 0 }}>
              Validation Guardrails Evaluation
            </div>
            <div className="validation-badges">
              <span className={`badge badge-val-${(validation.status || 'pass').toLowerCase()}`}>
                Status: {validation.status}
              </span>
              {validation.score != null && (
                <span className="badge badge-tech">
                  Score: {Math.round(validation.score * 100)}%
                </span>
              )}
              {validation.checked_items != null && (
                <span className="badge badge-tech">
                  Checks: {validation.checked_items - (validation.failed_items || 0)}/{validation.checked_items} Passed
                </span>
              )}
              {validation.validation_duration_ms != null && (
                <span className="badge badge-tech">
                  {validation.validation_duration_ms.toFixed(1)} ms
                </span>
              )}
            </div>
          </div>

          {validation.issues && validation.issues.length > 0 ? (
            <div className="validation-issues-list">
              {validation.issues.map((iss, idx) => (
                <div key={idx} className={`validation-issue-item severity-${(iss.severity || 'info').toLowerCase()}`}>
                  <div className="issue-header">
                    <span className={`severity-tag severity-${(iss.severity || 'info').toLowerCase()}`}>
                      {iss.severity}
                    </span>
                    <span className="issue-code">{iss.code}</span>
                    <span className="issue-category">[{iss.category}]</span>
                    {iss.recoverable && <span className="recoverable-tag">Auto-Recoverable</span>}
                  </div>
                  <div className="issue-message">{iss.message}</div>
                  {iss.evidence && <div className="issue-evidence">Evidence: <code>{iss.evidence}</code></div>}
                </div>
              ))}
            </div>
          ) : (
            <div className="validation-clean-box">
              <span>All automated guardrails passed: Response schema, numerical consistency, citation provenance, tool outputs, and claim assertions verified.</span>
            </div>
          )}
        </div>
      )}

      {sources && sources.length > 0 && (
        <div className="sources-section">
          <div className="section-label">
            Grounding Evidence & Citations ({sources.length})
          </div>
          <div className="sources-grid">
            {sources.map((src, idx) => (
              <div key={idx} className="source-card">
                <div className="source-card-header">
                  <div className="source-title-group">
                    <strong className="source-doc-name">{src.filename || 'Document'}</strong>
                    {src.page_number && (
                      <span className="source-page-badge">Page {src.page_number}</span>
                    )}
                  </div>
                  {src.similarity_score != null && (
                    <span className="source-score-badge">
                      Similarity: {(src.similarity_score * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                {src.snippet && (
                  <p className="source-snippet">
                    "{src.snippet}"
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
