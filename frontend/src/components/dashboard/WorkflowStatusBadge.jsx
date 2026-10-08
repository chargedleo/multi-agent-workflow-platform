import React from 'react';

/**
 * Standardized status badge with semantic color and iconography.
 */
export function WorkflowStatusBadge({ status, size = 'normal' }) {
  const normStatus = (status || 'UNKNOWN').toUpperCase();

  let badgeClass = 'status-pending';
  let icon = '⏳';
  let label = normStatus;

  switch (normStatus) {
    case 'COMPLETED':
      badgeClass = 'status-completed';
      icon = '✓';
      label = 'Completed';
      break;
    case 'RUNNING':
      badgeClass = 'status-running';
      icon = '🔄';
      label = 'Running';
      break;
    case 'PENDING':
      badgeClass = 'status-pending';
      icon = '⏳';
      label = 'Pending';
      break;
    case 'WAITING_FOR_APPROVAL':
    case 'AWAITING_APPROVAL':
      badgeClass = 'status-waiting_for_approval';
      icon = '👤';
      label = 'Awaiting Approval';
      break;
    case 'APPROVED':
      badgeClass = 'status-approved';
      icon = '✓';
      label = 'Approved';
      break;
    case 'FAILED':
      badgeClass = 'status-failed';
      icon = '✕';
      label = 'Failed';
      break;
    case 'CANCELLED':
    case 'REJECTED':
      badgeClass = 'status-rejected';
      icon = '⊘';
      label = normStatus === 'CANCELLED' ? 'Cancelled' : 'Rejected';
      break;
    case 'CHANGES_REQUESTED':
      badgeClass = 'status-changes_requested';
      icon = '↺';
      label = 'Changes Requested';
      break;
    default:
      badgeClass = 'status-unknown';
      icon = '•';
      label = status || 'Unknown';
      break;
  }

  const isSmall = size === 'small';

  return (
    <span
      className={`status-badge ${badgeClass} ${isSmall ? 'status-badge-sm' : ''}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
    >
      <span className="status-badge-icon" aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </span>
  );
}

export default WorkflowStatusBadge;
