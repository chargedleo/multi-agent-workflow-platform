import React, { useState } from 'react';
import { submitApprovalDecision } from '../services/api';

/**
 * Interactive Human-in-the-Loop Approval Card.
 * Allows human reviewers to inspect candidate workflow outputs, validation metrics,
 * and submit APPROVE, REJECT, or CHANGES_REQUESTED decisions to resume LangGraph execution.
 */
export function ApprovalCard({ runId, result, onDecisionSubmitted }) {
  const [feedback, setFeedback] = useState('');
  const [decidedBy, setDecidedBy] = useState('human_reviewer');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!result && !runId) return null;

  const activeRunId = runId || result?.run_id || result?.id;
  const answer = result?.answer || result?.final_answer || result?.candidate_answer;
  const validation = result?.validation;
  const revision = result?.approval_revision ?? 1;
  const maxRevisions = 3;

  const handleDecision = async (decision) => {
    setError(null);

    if (decision === 'CHANGES_REQUESTED' && (!feedback || !feedback.trim())) {
      setError('Please provide feedback or specific revision instructions when requesting changes.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await submitApprovalDecision(activeRunId, {
        decision,
        feedback: feedback.trim(),
        decided_by: decidedBy.trim() || 'human_reviewer',
      });

      if (onDecisionSubmitted) {
        onDecisionSubmitted(response);
      }
    } catch (err) {
      setError(err.message || `Failed to submit decision: ${decision}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="approval-card">
      <div className="approval-header">
        <div className="approval-title-group">
          <span className="approval-gate-icon">🛡️</span>
          <div>
            <h3 className="approval-title">Human-in-the-Loop Review Gate</h3>
            <p className="approval-subtitle">
              Workflow suspended at approval checkpoint. Review the synthesized output and guardrail metrics before releasing to production.
            </p>
          </div>
        </div>
        <div className="approval-badges">
          <span className="badge badge-approval-waiting">
            <span className="pulse-dot"></span>
            WAITING FOR APPROVAL
          </span>
          <span className="badge badge-tech">
            Revision {revision} of {maxRevisions}
          </span>
        </div>
      </div>

      {error && (
        <div className="error-banner" style={{ margin: '0.75rem 0' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Candidate answer preview */}
      {answer && (
        <div className="approval-preview-box">
          <div className="approval-preview-label">Draft Synthesized Answer for Review:</div>
          <div className="approval-preview-body">{answer}</div>
        </div>
      )}

      {/* Guardrail evaluation summary */}
      {validation && (
        <div className="approval-guardrail-summary">
          <span className="guardrail-summary-label">Automated Guardrails:</span>
          <span className={`badge badge-val-${(validation.status || 'pass').toLowerCase()}`}>
            Status: {validation.status}
          </span>
          {validation.score != null && (
            <span className="badge badge-tech">
              Score: {Math.round(validation.score * 100)}%
            </span>
          )}
          {validation.issues && validation.issues.length > 0 ? (
            <span className="badge badge-warning">
              {validation.issues.length} Guardrail Notice{validation.issues.length > 1 ? 's' : ''}
            </span>
          ) : (
            <span className="badge badge-success">0 Violations</span>
          )}
        </div>
      )}

      {/* Reviewer inputs */}
      <div className="approval-form-row">
        <div className="form-group reviewer-input-group">
          <label htmlFor="reviewer-name">Reviewer Identity:</label>
          <input
            id="reviewer-name"
            type="text"
            className="input-field"
            value={decidedBy}
            onChange={(e) => setDecidedBy(e.target.value)}
            disabled={isSubmitting}
            placeholder="e.g. lead_auditor, compliance_team"
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="reviewer-feedback">Reviewer Feedback & Revision Instructions:</label>
        <textarea
          id="reviewer-feedback"
          className="approval-textarea"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={isSubmitting}
          placeholder="Enter revision notes for the response agent, or notes explaining approval / rejection..."
          rows={3}
        />
      </div>

      {/* Action controls */}
      <div className="approval-actions-bar">
        <button
          type="button"
          className="btn-decision btn-approve"
          onClick={() => handleDecision('APPROVE')}
          disabled={isSubmitting}
        >
          <span className="btn-icon">✓</span>
          {isSubmitting ? 'Resuming...' : 'Approve & Finalize'}
        </button>

        <button
          type="button"
          className="btn-decision btn-changes"
          onClick={() => handleDecision('CHANGES_REQUESTED')}
          disabled={isSubmitting}
        >
          <span className="btn-icon">↺</span>
          {isSubmitting ? 'Resuming...' : 'Request Changes'}
        </button>

        <button
          type="button"
          className="btn-decision btn-reject"
          onClick={() => handleDecision('REJECT')}
          disabled={isSubmitting}
        >
          <span className="btn-icon">✕</span>
          {isSubmitting ? 'Resuming...' : 'Reject Workflow'}
        </button>
      </div>
    </div>
  );
}

export default ApprovalCard;
