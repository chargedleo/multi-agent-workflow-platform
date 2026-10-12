import React from 'react';

/**
 * Pending Approvals Component.
 * Displays workflows currently suspended at the Human-in-the-Loop review gate.
 */
export function PendingApprovals({ pendingApprovals = [], isLoading = false, onSelectApproval, onRefresh }) {
  if (isLoading && (!pendingApprovals || pendingApprovals.length === 0)) {
    return (
      <div className="section-container pending-section">
        <div className="pending-header">
          <div>
            <h2 className="dashboard-section-title">Pending Human Approvals</h2>
            <p className="dashboard-section-subtitle">Workflows suspended at review gate</p>
          </div>
        </div>
        <p className="empty-subtext">Loading pending approval requests...</p>
      </div>
    );
  }

  return (
    <div className="section-container pending-section">
      <div className="pending-header">
        <div>
          <h2 className="dashboard-section-title">Pending Human Approvals</h2>
          <p className="dashboard-section-subtitle">
            {pendingApprovals.length} {pendingApprovals.length === 1 ? 'workflow awaiting decision' : 'workflows awaiting decision'}
          </p>
        </div>
        <button
          type="button"
          className="btn-text-action"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh pending approvals"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {pendingApprovals.length === 0 ? (
        <div className="pending-empty-state">
          <p className="empty-title">All Workflows Approved or Completed</p>
          <p className="empty-subtext">
            No workflows are currently paused at the human review checkpoint. Workflows executed with approval enabled will appear here for review.
          </p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="workflow-runs-table">
            <thead>
              <tr>
                <th style={{ width: '130px' }}>Run ID</th>
                <th>Query</th>
                <th style={{ width: '140px' }}>Validation</th>
                <th style={{ width: '110px' }}>Revision</th>
                <th style={{ width: '130px' }}>Requested At</th>
                <th style={{ width: '110px', textAlign: 'center' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {pendingApprovals.map((item) => {
                const runId = item.run_id;
                const valStatus = (item.validation_status || 'pass').toLowerCase();
                const formattedTime = item.created_at
                  ? new Date(item.created_at).toLocaleTimeString()
                  : 'Just now';

                return (
                  <tr key={runId} className="workflow-run-row">
                    <td className="pending-id-cell">
                      <span className="mono-subtext" title={runId}>
                        {runId ? runId.slice(0, 10) + '...' : 'N/A'}
                      </span>
                    </td>
                    <td className="pending-query-cell" title={item.query}>
                      <span className="query-text-primary">
                        {item.query
                          ? item.query.length > 70
                            ? item.query.slice(0, 70) + '...'
                            : item.query
                          : 'No query text'}
                      </span>
                    </td>
                    <td>
                      <span className={`status-label status-val-${valStatus}`}>
                        {item.validation_status || 'PASS'}
                        {item.validation_score != null ? ` (${Math.round(item.validation_score * 100)}%)` : ''}
                      </span>
                    </td>
                    <td>
                      <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
                        Rev {item.approval_revision ?? 1}
                      </span>
                    </td>
                    <td className="timestamp-cell">{formattedTime}</td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        type="button"
                        className="btn-text-action"
                        onClick={() => onSelectApproval(runId)}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default PendingApprovals;
