import React, { useState, useEffect } from 'react';
import { WorkflowStatusBadge } from './WorkflowStatusBadge';

const STATUS_FILTERS = [
  { id: 'ALL', label: 'All Runs' },
  { id: 'ACTIVE', label: 'Active / Running' },
  { id: 'WAITING_FOR_APPROVAL', label: 'Awaiting Approval' },
  { id: 'COMPLETED', label: 'Completed' },
  { id: 'FAILED', label: 'Failed' },
  { id: 'REJECTED', label: 'Rejected' },
];

/**
 * Enterprise workflow run monitoring table with live filters, search, and pagination.
 */
export function WorkflowTable({
  runs = [],
  total = 0,
  page = 1,
  pageSize = 10,
  statusFilter = 'ALL',
  searchQuery = '',
  isLoading = false,
  autoRefreshInterval = 10,
  isPausedDueToVisibility = false,
  onPageChange,
  onPageSizeChange,
  onStatusFilterChange,
  onSearchChange,
  onAutoRefreshChange,
  onSelectRun,
  onRefresh,
}) {
  const [searchInput, setSearchInput] = useState(searchQuery);
  const [copiedId, setCopiedId] = useState(null);

  // Sync internal search input with external prop
  useEffect(() => {
    setSearchInput(searchQuery);
  }, [searchQuery]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (onSearchChange) {
      onSearchChange(searchInput.trim());
    }
  };

  const handleClearSearch = () => {
    setSearchInput('');
    if (onSearchChange) {
      onSearchChange('');
    }
  };

  const handleCopyId = (e, runId) => {
    e.stopPropagation();
    if (navigator.clipboard) {
      navigator.clipboard.writeText(runId);
      setCopiedId(runId);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="workflow-table-card">
      {/* Top Filter and Controls Bar */}
      <div className="table-controls-bar">
        {/* Search input form */}
        <form className="search-form" onSubmit={handleSearchSubmit}>
          <div className="search-input-wrapper">
            <input
              type="text"
              className="search-input"
              placeholder="Search by query text, run ID, or request ID..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            {searchInput && (
              <button
                type="button"
                className="btn-clear-search"
                onClick={handleClearSearch}
                title="Clear search"
              >
                &times;
              </button>
            )}
          </div>
          <button type="submit" className="btn-search-submit">
            Search
          </button>
        </form>

        {/* Live Refresh and Auto-refresh controls */}
        <div className="table-actions-right">
          <div className="auto-refresh-selector">
            <label htmlFor="auto-refresh-select" className="auto-refresh-label">
              Auto-Refresh:
            </label>
            <select
              id="auto-refresh-select"
              className="auto-refresh-dropdown"
              value={autoRefreshInterval}
              onChange={(e) => onAutoRefreshChange && onAutoRefreshChange(Number(e.target.value))}
            >
              <option value={0}>Off</option>
              <option value={5}>Every 5s</option>
              <option value={10}>Every 10s</option>
              <option value={30}>Every 30s</option>
            </select>
            {isPausedDueToVisibility && autoRefreshInterval > 0 && (
              <span className="paused-indicator" title="Auto-refresh paused while tab is inactive">
                (Paused)
              </span>
            )}
          </div>

          <button
            className="btn-text-action"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh runs"
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="status-filter-tabs">
        {STATUS_FILTERS.map((tab) => (
          <button
            key={tab.id}
            className={`status-filter-tab ${statusFilter === tab.id ? 'active' : ''}`}
            onClick={() => onStatusFilterChange && onStatusFilterChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Table Content */}
      {isLoading && runs.length === 0 ? (
        <div className="table-loading-state">
          <div className="spinner-sm" />
          <span>Querying PostgreSQL run history...</span>
        </div>
      ) : runs.length === 0 ? (
        <div className="table-empty-state">
          <p className="empty-primary">No workflow runs found matching the current criteria.</p>
          <span className="empty-subtext">
            {searchQuery || statusFilter !== 'ALL'
              ? 'Try adjusting your search terms or clearing status filters.'
              : 'Submit a new query using the Query Runner to create the first workflow execution!'}
          </span>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="workflow-runs-table">
            <thead>
              <tr>
                <th style={{ width: '130px' }}>Status</th>
                <th>Query & Run ID</th>
                <th style={{ width: '130px' }}>Stage</th>
                <th style={{ width: '110px' }}>Executed</th>
                <th style={{ width: '100px' }}>Duration</th>
                <th style={{ width: '110px' }}>Guardrails</th>
                <th style={{ width: '120px' }}>Approval</th>
                <th style={{ width: '90px', textAlign: 'center' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const runId = run.run_id || run.id;
                const durationText = run.duration_ms != null
                  ? `${(run.duration_ms / 1000).toFixed(2)}s`
                  : 'In progress';

                const timestamp = run.created_at || run.started_at;
                const timeText = timestamp
                  ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                  : '—';

                const stageName = (run.current_stage || (run.status === 'COMPLETED' ? 'Finalized' : 'Processing')).replace(/_/g, ' ');

                return (
                  <tr
                    key={runId}
                    className="workflow-run-row"
                    onClick={() => onSelectRun && onSelectRun(runId)}
                  >
                    <td>
                      <WorkflowStatusBadge status={run.status} size="small" />
                    </td>
                    <td className="query-cell">
                      <div className="query-text-primary" title={run.query || run.user_query}>
                        {run.query || run.user_query}
                      </div>
                      <div className="run-id-row">
                        <span className="mono-subtext">ID: {String(runId).substring(0, 10)}...</span>
                        <button
                          type="button"
                          className="btn-copy-id"
                          onClick={(e) => handleCopyId(e, String(runId))}
                          title="Copy full UUID"
                        >
                          {copiedId === String(runId) ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                    </td>
                    <td>
                      <span className="stage-pill">
                        {stageName}
                      </span>
                    </td>
                    <td className="timestamp-cell">{timeText}</td>
                    <td className="duration-cell">{durationText}</td>
                    <td>
                      {run.validation_status ? (
                        <span className={`status-label status-val-${run.validation_status.toLowerCase()}`}>
                          {run.validation_status}
                        </span>
                      ) : (
                        <span className="text-muted" style={{ fontSize: '0.85rem' }}>—</span>
                      )}
                    </td>
                    <td>
                      {run.approval_status ? (
                        <span className={`status-label status-appr-${run.approval_status.toLowerCase()}`}>
                          {run.approval_status}
                        </span>
                      ) : (
                        <span className="text-muted" style={{ fontSize: '0.85rem' }}>None</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn-text-action"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRun && onSelectRun(runId);
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

      {/* Pagination Controls */}
      <div className="table-pagination-bar">
        <div className="pagination-info">
          Showing <strong>{runs.length}</strong> of <strong>{total}</strong> runs recorded
        </div>

        <div className="pagination-controls">
          <div className="page-size-selector">
            <label htmlFor="page-size-select" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Rows:
            </label>
            <select
              id="page-size-select"
              className="page-size-dropdown"
              value={pageSize}
              onChange={(e) => onPageSizeChange && onPageSizeChange(Number(e.target.value))}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>

          <button
            className="btn-page-nav"
            onClick={() => onPageChange && onPageChange(page - 1)}
            disabled={page <= 1 || isLoading}
          >
            ← Previous
          </button>
          <span className="page-current-indicator">
            Page {page} of {totalPages}
          </span>
          <button
            className="btn-page-nav"
            onClick={() => onPageChange && onPageChange(page + 1)}
            disabled={page >= totalPages || isLoading}
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}

export default WorkflowTable;
