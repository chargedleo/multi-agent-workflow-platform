import React from 'react';

export function WorkflowHistory({ runs, isLoading, onSelectRun, onRefresh }) {
  return (
    <div className="history-card">
      <div className="history-header">
        <div className="history-title-group">
          <h3 className="history-title">Persistent Workflow Run History</h3>
          <span className="history-subtitle">Backed by PostgreSQL durable run records</span>
        </div>
        <button 
          className="btn-refresh" 
          onClick={onRefresh} 
          disabled={isLoading}
          title="Refresh run history"
        >
          {isLoading ? 'Refreshing...' : 'Refresh History'}
        </button>
      </div>

      {isLoading && runs.length === 0 ? (
        <div className="history-loading">Loading execution history...</div>
      ) : runs.length === 0 ? (
        <div className="history-empty">
          <p>No workflow runs recorded yet. Execute a query above to create the first persistent run!</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="runs-table">
            <thead>
              <tr>
                <th className="col-hist-status">Status</th>
                <th className="col-hist-query">Query</th>
                <th className="col-hist-duration">Duration</th>
                <th className="col-hist-time">Executed At</th>
                <th className="col-hist-steps">Steps</th>
                <th className="col-hist-action" style={{ textAlign: 'center' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const statusClass = (run.status || '').toLowerCase();
                const runId = run.run_id || run.id;
                const durationText = run.duration_ms != null ? `${(run.duration_ms / 1000).toFixed(2)}s` : '—';
                const createdDate = run.created_at ? new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';

                return (
                  <tr key={runId} className="run-row" onClick={() => onSelectRun(runId)}>
                    <td className="col-hist-status">
                      <span className={`status-badge status-${statusClass}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="col-hist-query query-cell" title={run.user_query}>
                      <span className="query-text-truncate">{run.user_query}</span>
                      <span className="mono-subtext">ID: {String(runId).substring(0, 8)}...</span>
                    </td>
                    <td className="col-hist-duration">{durationText}</td>
                    <td className="col-hist-time">{createdDate}</td>
                    <td className="col-hist-steps">{run.step_count ?? 3} steps</td>
                    <td className="col-hist-action" style={{ textAlign: 'center' }}>
                      <button 
                        className="btn-text-action"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRun(runId);
                        }}
                      >
                        Inspect
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
