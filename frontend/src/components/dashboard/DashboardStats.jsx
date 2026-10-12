import React from 'react';

/**
 * Clean analytical metric indicator without decorative boxes or icons.
 */
function MetricItem({ title, value, subtitle, badgeText }) {
  return (
    <div className="metric-stat-item">
      <div className="metric-stat-value-row">
        <div className="metric-stat-value">{value}</div>
        {badgeText && <span className="metric-stat-badge">{badgeText}</span>}
      </div>
      <div className="metric-stat-label">{title}</div>
      {subtitle && <div className="metric-stat-subtitle">{subtitle}</div>}
    </div>
  );
}

/**
 * Analytical Metrics Summary bar showing real-time PostgreSQL operational statistics.
 * Formatted as a unified, clean horizontal analytical report rather than separate boxed cards.
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
    <section className="dashboard-stats-section">
      <div className="dashboard-stats-header">
        <div>
          <h2 className="dashboard-section-title">Workflow Metrics</h2>
          <p className="dashboard-section-subtitle">Real-time indicators aggregated across PostgreSQL run history</p>
        </div>
        {onRefresh && (
          <button
            className="btn-text-action"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh metrics"
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        )}
      </div>

      <div className="dashboard-metrics-summary">
        <MetricItem
          title="Total Runs"
          value={s.total_runs.toLocaleString()}
          subtitle="All recorded runs"
        />
        <MetricItem
          title="Active / Running"
          value={s.active_runs.toLocaleString()}
          subtitle="Processing in LangGraph"
        />
        <MetricItem
          title="Awaiting Approval"
          value={s.awaiting_approval.toLocaleString()}
          subtitle="Suspended at HITL gate"
          badgeText={s.awaiting_approval > 0 ? 'Action needed' : undefined}
        />
        <MetricItem
          title="Completed"
          value={s.completed_runs.toLocaleString()}
          subtitle={s.total_runs > 0 ? `${Math.round((s.completed_runs / s.total_runs) * 100)}% success rate` : 'Finished cleanly'}
        />
        <MetricItem
          title="Failed"
          value={s.failed_runs.toLocaleString()}
          subtitle="Execution errors"
        />
        <MetricItem
          title="Rejected"
          value={s.rejected_runs.toLocaleString()}
          subtitle="Disapproved by reviewer"
        />
        <MetricItem
          title="Average Duration"
          value={avgDurationText}
          subtitle="Completed latency"
        />
      </div>
    </section>
  );
}

export default DashboardStats;
