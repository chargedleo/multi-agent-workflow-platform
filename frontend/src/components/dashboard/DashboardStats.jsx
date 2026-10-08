import React from 'react';

/**
 * Metric card displaying aggregated operational indicators.
 */
function MetricCard({ title, value, subtitle, icon, variant = 'default', badgeText }) {
  return (
    <div className={`metric-card metric-card-${variant}`}>
      <div className="metric-card-header">
        <span className="metric-card-title">{title}</span>
        <span className="metric-card-icon">{icon}</span>
      </div>
      <div className="metric-card-body">
        <div className="metric-card-value">{value}</div>
        {badgeText && (
          <span className="metric-card-badge">{badgeText}</span>
        )}
      </div>
      {subtitle && <div className="metric-card-subtitle">{subtitle}</div>}
    </div>
  );
}

/**
 * Executive Metrics Bar showing real-time PostgreSQL operational statistics.
 */
export function DashboardStats({ stats, isLoading, onRefresh }) {
  const s = stats || {
    total_runs: 0,
    active_runs: 0,
    awaiting_approval: 0,
    completed_runs: 0,
    failed_runs: 0,
    rejected_runs: 0,
    avg_duration_ms: null,
  };

  const avgDurationText = s.avg_duration_ms != null
    ? `${(s.avg_duration_ms / 1000).toFixed(2)}s`
    : '—';

  return (
    <div className="dashboard-stats-container">
      <div className="dashboard-stats-header">
        <div className="stats-header-left">
          <h3 className="dashboard-section-title">Executive Workflow Metrics</h3>
          <span className="dashboard-section-subtitle">Real-time metrics aggregated across PostgreSQL run history</span>
        </div>
        {onRefresh && (
          <button
            className="btn-stats-refresh"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh metrics"
          >
            {isLoading ? '↻ Refreshing...' : '↻ Refresh Metrics'}
          </button>
        )}
      </div>

      <div className="dashboard-stats-grid">
        <MetricCard
          title="Total Runs"
          value={s.total_runs.toLocaleString()}
          subtitle="All recorded executions"
          icon="⚡"
          variant="primary"
        />
        <MetricCard
          title="Active / Running"
          value={s.active_runs.toLocaleString()}
          subtitle="Processing in LangGraph"
          icon="🔄"
          variant={s.active_runs > 0 ? 'running' : 'default'}
        />
        <MetricCard
          title="Awaiting Approval"
          value={s.awaiting_approval.toLocaleString()}
          subtitle="Suspended at HITL gate"
          icon="👤"
          variant={s.awaiting_approval > 0 ? 'warning' : 'default'}
          badgeText={s.awaiting_approval > 0 ? 'Action Needed' : undefined}
        />
        <MetricCard
          title="Completed"
          value={s.completed_runs.toLocaleString()}
          subtitle={s.total_runs > 0 ? `${Math.round((s.completed_runs / s.total_runs) * 100)}% success rate` : 'Finished cleanly'}
          icon="✓"
          variant="success"
        />
        <MetricCard
          title="Failed"
          value={s.failed_runs.toLocaleString()}
          subtitle="Guardrail or execution failure"
          icon="✕"
          variant={s.failed_runs > 0 ? 'danger' : 'default'}
        />
        <MetricCard
          title="Rejected / Cancelled"
          value={s.rejected_runs.toLocaleString()}
          subtitle="Disapproved by reviewer"
          icon="⊘"
          variant={s.rejected_runs > 0 ? 'muted-danger' : 'default'}
        />
        <MetricCard
          title="Avg Duration"
          value={avgDurationText}
          subtitle="Completed runs latency"
          icon="⏱"
          variant="info"
        />
      </div>
    </div>
  );
}

export default DashboardStats;
