import React from 'react';
import { DashboardStats } from './DashboardStats';
import { WorkflowTable } from './WorkflowTable';

/**
 * Enterprise Multi-Agent AI Workflow Monitoring Dashboard root view.
 */
export function Dashboard({
  stats,
  isStatsLoading,
  runs,
  totalRuns,
  page,
  pageSize,
  statusFilter,
  searchQuery,
  isRunsLoading,
  autoRefreshInterval,
  isPausedDueToVisibility,
  pendingApprovals = [],
  onPageChange,
  onPageSizeChange,
  onStatusFilterChange,
  onSearchChange,
  onAutoRefreshChange,
  onSelectRun,
  onRefreshAll,
  onNavigateToApprovals,
}) {
  return (
    <div className="dashboard-root-view">
      {/* 1. Executive Metrics Statistics */}
      <DashboardStats
        stats={stats}
        isLoading={isStatsLoading}
        onRefresh={onRefreshAll}
      />

      {/* 2. Pending Approvals Alert Banner if any workflows are suspended */}
      {pendingApprovals && pendingApprovals.length > 0 && (
        <div className="pending-approvals-alert-banner">
          <div className="alert-banner-left">
            <div>
              <h3 className="alert-banner-title">
                {pendingApprovals.length} {pendingApprovals.length === 1 ? 'Workflow Run Requires' : 'Workflow Runs Require'} Human Review
              </h3>
              <p className="alert-banner-desc">
                Workflows suspended at the checkpoint awaiting reviewer authorization.
              </p>
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={onNavigateToApprovals}
          >
            Review Pending Queue ({pendingApprovals.length})
          </button>
        </div>
      )}

      {/* 3. Filterable, Searchable, Paginated Workflow Runs Table */}
      <WorkflowTable
        runs={runs}
        total={totalRuns}
        page={page}
        pageSize={pageSize}
        statusFilter={statusFilter}
        searchQuery={searchQuery}
        isLoading={isRunsLoading}
        autoRefreshInterval={autoRefreshInterval}
        isPausedDueToVisibility={isPausedDueToVisibility}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        onStatusFilterChange={onStatusFilterChange}
        onSearchChange={onSearchChange}
        onAutoRefreshChange={onAutoRefreshChange}
        onSelectRun={onSelectRun}
        onRefresh={onRefreshAll}
      />
    </div>
  );
}

export default Dashboard;
