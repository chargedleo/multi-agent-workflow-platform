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
          {isLoading ? 'Refreshing...' : '↻ Refresh History'}
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
                <th>Status</th>
                <th>Query</th>
                <th>Duration</th>
                <th>Executed At</th>
                <th>Steps</th>
                <th>Action</th>
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
                    <td>
                      <span className={`status-badge status-${statusClass}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="query-cell" title={run.user_query}>
                      <span className="query-text-truncate">{run.user_query}</span>
                      <span className="mono-subtext">ID: {String(runId).substring(0, 8)}...</span>
                    </td>
                    <td>{durationText}</td>
                    <td>{createdDate}</td>
                    <td>{run.step_count ?? 3} steps</td>
                    <td>
                      <button 
                        className="btn-table-action"
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
