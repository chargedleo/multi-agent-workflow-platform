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
          {run.final_answer && (
            <div className="detail-section">
              <h4 className="detail-heading">Synthesized Final Answer</h4>
              <div className="final-answer-box">{run.final_answer}</div>
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
