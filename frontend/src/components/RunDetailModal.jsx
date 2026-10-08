import React, { useState } from 'react';
import { ApprovalCard } from './ApprovalCard';
import { WorkflowTimeline } from './dashboard/WorkflowTimeline';
import { WorkflowStatusBadge } from './dashboard/WorkflowStatusBadge';

export function RunDetailModal({ run, onClose, onApprovalDone }) {
  const [activeTab, setActiveTab] = useState('all');

  if (!run) return null;

  const durationText = run.duration_ms != null
    ? `${(run.duration_ms / 1000).toFixed(2)}s (${run.duration_ms} ms)`
    : 'In progress';

  const stepsCount = run.steps ? run.steps.length : 0;
  const sourcesCount = (run.sources || run.metadata?.sources || []).length;
  const approvalsCount = (run.approvals || []).length;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-content-lg" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h2 className="modal-title">Workflow Execution Run Details</h2>
              <WorkflowStatusBadge status={run.status} />
              {run.approval_status && (
                <span className={`status-badge status-${run.approval_status.toLowerCase()}`}>
                  Approval: {run.approval_status}
                </span>
              )}
            </div>
            <div className="modal-meta-row" style={{ marginTop: '0.35rem' }}>
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

        {/* Modal Navigation Tabs */}
        <div className="modal-tabs-bar">
          <button
            className={`modal-tab ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            📋 Comprehensive View
          </button>
          <button
            className={`modal-tab ${activeTab === 'timeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('timeline')}
          >
            ⚡ Execution Stages ({stepsCount})
          </button>
          <button
            className={`modal-tab ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => setActiveTab('results')}
          >
            ✨ Output & Synthesis
          </button>
          <button
            className={`modal-tab ${activeTab === 'guardrails' ? 'active' : ''}`}
            onClick={() => setActiveTab('guardrails')}
          >
            🛡️ Guardrails & MCP
          </button>
          <button
            className={`modal-tab ${activeTab === 'approvals' ? 'active' : ''}`}
            onClick={() => setActiveTab('approvals')}
          >
            👤 HITL Approval ({approvalsCount})
          </button>
        </div>

        <div className="modal-body">
          {/* Multi-Agent Execution Stage Visualizer (Always shown or prominent in timeline) */}
          <div className="detail-section" style={{ paddingBottom: '0.5rem' }}>
            <h4 className="detail-heading">Multi-Agent Pipeline Progression</h4>
            <WorkflowTimeline run={run} interactive={true} />
          </div>

          {/* User Query Box */}
          <div className="detail-section">
            <h4 className="detail-heading">Submitted User Query</h4>
            <div className="query-box">{run.query || run.user_query}</div>
          </div>

          {/* Key Execution Metrics Grid */}
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
              <div className="metric-title">Guardrails Status</div>
              <div className="metric-value">
                {run.validation_status ? (
                  <span className={`status-badge status-${run.validation_status.toLowerCase()}`}>
                    {run.validation_status} {run.validation_score != null ? `(${Math.round(run.validation_score * 100)}%)` : ''}
                  </span>
                ) : 'N/A'}
              </div>
            </div>
            <div className="metric-box">
              <div className="metric-title">Approval Gate</div>
              <div className="metric-value">
                {run.approval_status ? (
                  <span className={`status-badge status-${run.approval_status.toLowerCase()}`}>
                    {run.approval_status}
                  </span>
                ) : 'NOT REQUIRED'}
              </div>
            </div>
            <div className="metric-box">
              <div className="metric-title">Recorded Steps</div>
              <div className="metric-value">{stepsCount}</div>
            </div>
            <div className="metric-box">
              <div className="metric-title">Executed At</div>
              <div className="metric-value">
                {run.started_at ? new Date(run.started_at).toLocaleTimeString() : 'N/A'}
              </div>
            </div>
          </div>

          {/* Active Approval Card if waiting for review */}
          {run.status === 'WAITING_FOR_APPROVAL' && (
            <div style={{ margin: '1.25rem 0' }}>
              <ApprovalCard
                runId={run.run_id || run.id}
                result={run}
                onDecisionSubmitted={(updated) => {
                  if (onApprovalDone) onApprovalDone(updated);
                  onClose();
                }}
              />
            </div>
          )}

          {/* Errors section if any */}
          {run.errors && run.errors.length > 0 && (
            <div className="error-banner" style={{ margin: '1rem 0' }}>
              <strong>Execution Errors Recorded:</strong>
              <ul>
                {run.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Section: Synthesized Final Answer */}
          {(activeTab === 'all' || activeTab === 'results') && (run.final_answer || run.answer) && (
            <div className="detail-section">
              <h4 className="detail-heading">Synthesized Final Answer</h4>
              <div className="final-answer-box">{run.final_answer || run.answer}</div>
              {run.key_points && run.key_points.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <strong>Key Strategic Takeaways:</strong>
                  <ul className="key-points-list">
                    {run.key_points.map((pt, idx) => (
                      <li key={idx}>{pt}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Section: Agent Steps Timeline */}
          {(activeTab === 'all' || activeTab === 'timeline') && (
            <div className="detail-section">
              <h4 className="detail-heading">Agent Execution Step History</h4>
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
          )}

          {/* Section: Quantitative Data Analysis (MCP) */}
          {(activeTab === 'all' || activeTab === 'guardrails') &&
            ((run.analysis_results && run.analysis_results.status === 'completed') || (run.metadata?.analysis_results && run.metadata.analysis_results.status === 'completed')) && (() => {
            const analysis = run.analysis_results || run.metadata.analysis_results;
            return (
              <div className="detail-section">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <h4 className="detail-heading" style={{ marginBottom: 0 }}>MCP PostgreSQL Analytics</h4>
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

          {/* Section: Validation Guardrails */}
          {(activeTab === 'all' || activeTab === 'guardrails') &&
            ((run.validation) || (run.metadata?.validation)) && (() => {
            const val = run.validation || run.metadata.validation;
            return (
              <div className="detail-section">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <h4 className="detail-heading" style={{ marginBottom: 0 }}>Validation Guardrails</h4>
                  <div className="validation-badges">
                    <span className={`badge badge-val-${(val.status || 'pass').toLowerCase()}`}>
                      Status: {val.status}
                    </span>
                    {val.score != null && (
                      <span className="badge badge-tech">
                        Score: {Math.round(val.score * 100)}%
                      </span>
                    )}
                    {val.checked_items != null && (
                      <span className="badge badge-tech">
                        Checks: {val.checked_items - (val.failed_items || 0)}/{val.checked_items} Passed
                      </span>
                    )}
                  </div>
                </div>

                {val.issues && val.issues.length > 0 ? (
                  <div className="validation-issues-list">
                    {val.issues.map((iss, idx) => (
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
                    <span className="validation-clean-icon">✅</span>
                    <span>All automated guardrails passed: Response schema, numerical consistency, citation provenance, tool outputs, and claim assertions verified.</span>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Section: Sources and citations */}
          {(activeTab === 'all' || activeTab === 'results') &&
            ((run.sources && run.sources.length > 0) || (run.metadata?.sources && run.metadata.sources.length > 0)) && (
            <div className="detail-section">
              <h4 className="detail-heading">FAISS Document Retrieval Citations ({sourcesCount})</h4>
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

          {/* Section: Human Approval Audit Trail */}
          {(activeTab === 'all' || activeTab === 'approvals') &&
            ((run.approvals && run.approvals.length > 0) || run.approval_status) && (
            <div className="detail-section">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <h4 className="detail-heading" style={{ marginBottom: 0 }}>Human-in-the-Loop Decision Audit History</h4>
                {run.approval_status && (
                  <span className={`status-badge status-${run.approval_status.toLowerCase()}`}>
                    Current State: {run.approval_status}
                  </span>
                )}
              </div>
              {run.approvals && run.approvals.length > 0 ? (
                <div className="approval-history-list">
                  {run.approvals.map((appr, idx) => (
                    <div key={appr.id || idx} className="approval-history-item">
                      <div className="approval-item-header">
                        <span className={`status-badge status-${(appr.decision || appr.status || '').toLowerCase()}`}>
                          {appr.decision || appr.status}
                        </span>
                        <span className="mono-badge">Revision #{appr.revision_count ?? idx}</span>
                        <span className="approval-reviewer-name">Reviewer: {appr.decided_by || 'system'}</span>
                        <span className="approval-time">
                          {appr.decided_at ? new Date(appr.decided_at).toLocaleTimeString() : appr.created_at ? new Date(appr.created_at).toLocaleTimeString() : ''}
                        </span>
                      </div>
                      {appr.feedback && (
                        <div className="approval-item-feedback">
                          <strong>Feedback / Notes:</strong> "{appr.feedback}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-subtext">No historical approval actions recorded yet.</p>
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

export default RunDetailModal;
