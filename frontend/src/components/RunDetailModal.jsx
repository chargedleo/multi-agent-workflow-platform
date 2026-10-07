import React from 'react';

export function RunDetailModal({ run, onClose }) {
  if (!run) return null;

  const statusClass = (run.status || '').toLowerCase();
  const durationText = run.duration_ms != null ? `${(run.duration_ms / 1000).toFixed(2)}s (${run.duration_ms} ms)` : 'In progress';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <h2 className="modal-title">Workflow Run Details</h2>
            <div className="modal-meta-row">
              <span className={`status-badge status-${statusClass}`}>
                {run.status}
              </span>
              <span className="mono-badge">Run ID: {run.run_id || run.id}</span>
              {run.request_id && (
                <span className="mono-badge">Request ID: {run.request_id}</span>
              )}
            </div>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        <div className="modal-body">
          {/* Query section */}
          <div className="detail-section">
            <h4 className="detail-heading">User Query</h4>
            <div className="query-box">{run.query || run.user_query}</div>
          </div>

          {/* Overview metrics */}
          <div className="metrics-grid">
            <div className="metric-box">
              <div className="metric-title">Duration</div>
              <div className="metric-value">{durationText}</div>
            </div>
            <div className="metric-box">
              <div className="metric-title">Confidence</div>
              <div className="metric-value">
                {run.confidence != null ? `${Math.round(run.confidence * 100)}%` : 'N/A'}
              </div>
            </div>
            <div className="metric-box">
              <div className="metric-title">Steps Executed</div>
              <div className="metric-value">{run.steps ? run.steps.length : 0}</div>
            </div>
            <div className="metric-box">
              <div className="metric-title">Started At</div>
              <div className="metric-value">
                {run.started_at ? new Date(run.started_at).toLocaleTimeString() : 'N/A'}
              </div>
            </div>
          </div>

          {/* Errors section if any */}
          {run.errors && run.errors.length > 0 && (
            <div className="error-banner" style={{ margin: '1rem 0' }}>
              <strong>Recorded Errors:</strong>
              <ul>
                {run.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Agent Steps Timeline */}
          <div className="detail-section">
            <h4 className="detail-heading">Agent Execution Steps</h4>
            <div className="steps-timeline">
              {run.steps && run.steps.length > 0 ? (
                run.steps.map((step) => {
                  const stepStatusClass = (step.status || '').toLowerCase();
                  return (
                    <div key={step.id || step.step_order} className="step-card">
                      <div className="step-card-header">
                        <div className="step-header-left">
                          <span className="step-order-badge">#{step.step_order}</span>
                          <span className="step-agent-name">{step.agent_name.toUpperCase()} AGENT</span>
                          <span className={`status-badge status-${stepStatusClass}`}>
                            {step.status}
                          </span>
                        </div>
                        <div className="step-header-right">
                          {step.duration_ms != null && (
                            <span className="step-duration">{step.duration_ms} ms</span>
                          )}
                        </div>
                      </div>

                      {step.error && (
                        <div className="step-error-msg">
                          <strong>Error:</strong> {step.error}
                        </div>
                      )}

                      {step.output_data && (
                        <div className="step-data-preview">
                          <details>
                            <summary>View Output Data</summary>
                            <pre className="json-preview">
                              {JSON.stringify(step.output_data, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <p className="empty-subtext">No step records found for this run.</p>
              )}
            </div>
          </div>

          {/* Final Synthesized Answer */}
          {(run.final_answer || run.answer) && (
            <div className="detail-section">
              <h4 className="detail-heading">Synthesized Final Answer</h4>
              <div className="final-answer-box">{run.final_answer || run.answer}</div>
              {run.key_points && run.key_points.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <strong>Key Points:</strong>
                  <ul className="key-points-list">
                    {run.key_points.map((pt, idx) => (
                      <li key={idx}>{pt}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Quantitative Data Analysis if present */}
          {((run.analysis_results && run.analysis_results.status === 'completed') || (run.metadata?.analysis_results && run.metadata.analysis_results.status === 'completed')) && (() => {
            const analysis = run.analysis_results || run.metadata.analysis_results;
            return (
              <div className="detail-section">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <h4 className="detail-heading" style={{ marginBottom: 0 }}>Data Analysis Results (MCP)</h4>
                  <div className="analysis-badges">
                    <span className="badge badge-tech">Tool: {analysis.tool_name || 'analyze_dataset'}</span>
                    <span className="badge badge-tech">Dataset: {analysis.dataset}</span>
                    <span className="badge badge-tech">Op: {analysis.operation}</span>
                  </div>
                </div>
                {analysis.summary && (
                  <div className="analysis-summary-box" style={{ marginBottom: '0.75rem' }}>
                    <span className="analysis-icon">📊</span>
                    <span>{analysis.summary}</span>
                  </div>
                )}
                {analysis.metrics && Object.keys(analysis.metrics).length > 0 && (
                  <div className="analysis-metrics-grid" style={{ marginBottom: '0.75rem' }}>
                    {Object.entries(analysis.metrics).map(([k, v]) => (
                      <div key={k} className="analysis-metric-card">
                        <div className="analysis-metric-label">{k.replace(/_/g, ' ').toUpperCase()}</div>
                        <div className="analysis-metric-value">
                          {typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })()}

          {/* Sources and citations if present */}
          {((run.sources && run.sources.length > 0) || (run.metadata?.sources && run.metadata.sources.length > 0)) && (
            <div className="detail-section">
              <h4 className="detail-heading">Retrieved Document Citations</h4>
              <div className="sources-grid">
                {(run.sources || run.metadata?.sources || []).map((src, idx) => (
                  <div key={idx} className="source-card">
                    <div className="source-card-header">
                      <span className="source-icon">📄</span>
                      <strong className="source-doc-name">{src.filename || 'Document'}</strong>
                      {src.page_number && <span className="source-page-badge">Page {src.page_number}</span>}
                      {src.similarity_score != null && (
                        <span className="source-score-badge">
                          Score: {(src.similarity_score * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    {src.snippet && <p className="source-snippet">"{src.snippet}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
