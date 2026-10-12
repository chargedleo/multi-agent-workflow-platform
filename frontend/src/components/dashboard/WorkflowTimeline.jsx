import React, { useState } from 'react';

/**
 * Stage definition for the multi-agent orchestration architecture.
 * Clean, restrained text without decorative emoji icons.
 */
const PIPELINE_STAGES = [
  {
    id: 'planner',
    agentName: 'planner',
    label: 'Planner',
    role: 'Decomposition',
    description: 'Decomposes query into execution strategy and assigns agent sub-tasks.',
  },
  {
    id: 'document_retrieval',
    agentName: 'document_retrieval',
    label: 'Retrieval',
    role: 'Vector Search',
    description: 'Performs semantic vector search across ingested documents via FAISS.',
  },
  {
    id: 'data_analysis',
    agentName: 'data_analysis',
    label: 'Data Analysis',
    role: 'MCP Analytics',
    description: 'Executes verified analytics queries against PostgreSQL through MCP tools.',
  },
  {
    id: 'researcher',
    agentName: 'researcher',
    label: 'Researcher',
    role: 'Synthesis',
    description: 'Synthesizes domain evidence, retrieved chunks, and quantitative trends.',
  },
  {
    id: 'responder',
    agentName: 'responder',
    label: 'Responder',
    role: 'Formulation',
    description: 'Compiles structured executive summary, key points, and citation references.',
  },
  {
    id: 'validation',
    agentName: 'validation',
    label: 'Validation',
    role: 'Guardrails',
    description: 'Validates claims, numerical bounds, citations, and hallucination guardrails.',
  },
  {
    id: 'human_approval',
    agentName: 'human_approval',
    label: 'Approval Gate',
    role: 'Human Review',
    description: 'Suspends execution for human oversight, accepting Approve / Reject / Changes.',
  },
  {
    id: 'finalization',
    agentName: 'finalization',
    label: 'Verified Output',
    role: 'Completion',
    description: 'Final verified release persisted in PostgreSQL run record.',
  },
];

/**
 * Execution Stage / Timeline Visualizer mapping LangGraph workflow stages.
 */
export function WorkflowTimeline({ run, interactive = true }) {
  const [selectedStage, setSelectedStage] = useState(null);

  const steps = run?.steps || [];
  const runStatus = (run?.status || '').toUpperCase();
  const approvalStatus = (run?.approval_status || '').toUpperCase();
  const isCompleted = runStatus === 'COMPLETED';
  const isWaitingApproval = runStatus === 'WAITING_FOR_APPROVAL';
  const isFailed = runStatus === 'FAILED';

  // Helper to determine status and step data for each stage
  const getStageState = (stage) => {
    const step = steps.find((s) => s.agent_name === stage.agentName);

    // Human Approval special gate
    if (stage.id === 'human_approval') {
      if (isWaitingApproval) {
        return { status: 'waiting', duration: null, step: null };
      }
      if (approvalStatus === 'APPROVED' || (isCompleted && !isWaitingApproval)) {
        return { status: 'completed', duration: null, step: null };
      }
      if (approvalStatus === 'REJECTED' || runStatus === 'CANCELLED') {
        return { status: 'rejected', duration: null, step: null };
      }
      if (isFailed && !step) {
        return { status: 'pending', duration: null, step: null };
      }
    }

    // Final output stage
    if (stage.id === 'finalization') {
      if (isCompleted) {
        return { status: 'completed', duration: null, step: null };
      }
      if (isFailed) {
        return { status: 'failed', duration: null, step: null };
      }
      return { status: 'pending', duration: null, step: null };
    }

    // Standard agent step evaluation
    if (step) {
      const sStatus = (step.status || '').toLowerCase();
      if (sStatus === 'completed') {
        return { status: 'completed', duration: step.duration_ms, step };
      }
      if (sStatus === 'failed') {
        return { status: 'failed', duration: step.duration_ms, step };
      }
      if (sStatus === 'running') {
        return { status: 'active', duration: step.duration_ms, step };
      }
    }

    if (isCompleted) {
      return { status: 'completed', duration: null, step: null };
    }

    if (isWaitingApproval) {
      const approvalIndex = PIPELINE_STAGES.findIndex((s) => s.id === 'human_approval');
      const currentIndex = PIPELINE_STAGES.findIndex((s) => s.id === stage.id);
      if (currentIndex < approvalIndex) {
        return { status: 'completed', duration: step?.duration_ms || null, step };
      }
    }

    return { status: 'pending', duration: null, step: null };
  };

  return (
    <div className="workflow-timeline-wrapper">
      <div className="workflow-timeline-container">
        {PIPELINE_STAGES.map((stage, idx) => {
          const { status, duration, step } = getStageState(stage);
          const isSelected = selectedStage?.id === stage.id;

          let nodeClass = 'timeline-pending';
          if (status === 'completed') nodeClass = 'timeline-completed';
          else if (status === 'active') nodeClass = 'timeline-active';
          else if (status === 'waiting') nodeClass = 'timeline-waiting';
          else if (status === 'failed') nodeClass = 'timeline-failed';
          else if (status === 'rejected') nodeClass = 'timeline-rejected';

          return (
            <React.Fragment key={stage.id}>
              <div
                className={`timeline-node ${nodeClass} ${isSelected ? 'timeline-node-selected' : ''}`}
                onClick={() => {
                  if (interactive) {
                    setSelectedStage(isSelected ? null : { stage, step, status, duration });
                  }
                }}
                title={`${stage.label} (${stage.role}): ${status}`}
                role={interactive ? 'button' : undefined}
                tabIndex={interactive ? 0 : undefined}
              >
                <span className="timeline-node-step">{idx + 1}</span>
                <div className="timeline-node-content">
                  <span className="timeline-node-label">{stage.label}</span>
                  <span className="timeline-node-role">{stage.role}</span>
                  {duration != null && (
                    <span className="timeline-node-duration">{duration}ms</span>
                  )}
                  {status === 'waiting' && (
                    <span className="timeline-node-status-text">Pending Review</span>
                  )}
                </div>
              </div>
              {idx < PIPELINE_STAGES.length - 1 && (
                <div className={`timeline-connector ${status === 'completed' ? 'connector-completed' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Selected stage details popover */}
      {selectedStage && (
        <div className="timeline-stage-detail-card">
          <div className="stage-detail-header">
            <div className="stage-detail-title-group">
              <div>
                <h4 className="stage-detail-title">{selectedStage.stage.label} — {selectedStage.stage.role}</h4>
                <p className="stage-detail-desc">{selectedStage.stage.description}</p>
              </div>
            </div>
            <button
              className="btn-close-sm"
              onClick={() => setSelectedStage(null)}
              aria-label="Close stage details"
            >
              &times;
            </button>
          </div>

          <div className="stage-detail-body">
            <div className="stage-detail-meta">
              <span>Status: <strong>{selectedStage.status.toUpperCase()}</strong></span>
              {selectedStage.duration != null && (
                <span>Duration: <strong>{selectedStage.duration} ms</strong></span>
              )}
              {selectedStage.step?.started_at && (
                <span>Started: {new Date(selectedStage.step.started_at).toLocaleTimeString()}</span>
              )}
            </div>

            {selectedStage.step?.error && (
              <div className="step-error-msg" style={{ marginTop: '0.5rem' }}>
                <strong>Error:</strong> {selectedStage.step.error}
              </div>
            )}

            {selectedStage.step?.output_data && (
              <details style={{ marginTop: '0.5rem' }}>
                <summary style={{ cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  View Step Output Data
                </summary>
                <pre className="json-preview" style={{ maxHeight: '180px', marginTop: '0.35rem' }}>
                  {JSON.stringify(selectedStage.step.output_data, null, 2)}
                </pre>
              </details>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkflowTimeline;
