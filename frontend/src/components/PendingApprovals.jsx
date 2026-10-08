import React from 'react';

/**
 * Pending Approvals Component.
 * Displays workflows currently suspended at the Human-in-the-Loop review gate.
 */
export function PendingApprovals({ pendingApprovals = [], isLoading = false, onSelectApproval, onRefresh }) {
  if (isLoading && (!pendingApprovals || pendingApprovals.length === 0)) {
    return (
      <div className="section-card pending-card">
        <div className="pending-header">
          <div className="pending-title-group">
            <span className="pending-icon">⏳</span>
            <h3 className="section-title">Pending Human Approvals</h3>
          </div>
        </div>
        <p className="empty-subtext">Loading pending approval requests...</p>
      </div>
    );
  }

  return (
    <div className="section-card pending-card">
      <div className="pending-header">
        <div className="pending-title-group">
          <span className="pending-icon">⏳</span>
          <h3 className="section-title">Pending Human Approvals</h3>
          <span className={`badge ${pendingApprovals.length > 0 ? 'badge-amber-pill' : 'badge-neutral'}`}>
            {pendingApprovals.length} Waiting
          </span>
        </div>
        <button
          type="button"
          className="btn-refresh"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh pending approvals"
        >
          {isLoading ? 'Refreshing...' : '↻ Refresh'}
        </button>
      </div>

      {pendingApprovals.length === 0 ? (
        <div className="pending-empty-state">
          <span className="empty-icon">✓</span>
          <p className="empty-title">All Workflows Approved or Completed</p>
          <p className="empty-subtext">
            No workflows are currently paused at the human review checkpoint. Workflows executed with approval enabled will appear here for review.
          </p>
        </div>
      ) : (
        <div className="pending-table-container">
          <table className="pending-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Query</th>
                <th>Validation</th>
                <th>Revision</th>
                <th>Requested At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {pendingApprovals.map((item) => {
                const runId = item.run_id;
                const reqId = item.request_id || item.run_id;
                const valStatus = (item.validation_status || 'pass').toLowerCase();
                const formattedTime = item.created_at
                  ? new Date(item.created_at).toLocaleTimeString()
                  : 'Just now';

                return (
                  <tr key={runId} className="pending-row">
                    <td className="pending-id-cell">
                      <span className="mono-badge" title={runId}>
                        {runId ? runId.slice(0, 8) + '...' : 'N/A'}
                      </span>
                    </td>
                    <td className="pending-query-cell" title={item.query}>
                      {item.query
                        ? item.query.length > 60
                          ? item.query.slice(0, 60) + '...'
                          : item.query
                        : 'No query text'}
                    </td>
                    <td>
                      <span className={`badge badge-val-${valStatus}`}>
                        {item.validation_status || 'PASS'}
                        {item.validation_score != null ? ` (${Math.round(item.validation_score * 100)}%)` : ''}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-tech">
                        Rev {item.approval_revision ?? 1}
                      </span>
                    </td>
                    <td className="pending-time-cell">{formattedTime}</td>
                    <td>
                      <button
                        type="button"
                        className="btn-review-action"
                        onClick={() => onSelectApproval(runId)}
                      >
                        Inspect & Decide →
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
