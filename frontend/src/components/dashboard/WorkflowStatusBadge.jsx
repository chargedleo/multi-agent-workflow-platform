import React from 'react';

/**
 * Restrained status indicator using clean typography and subtle semantic color.
 * Replaces bulky pill badges and decorative glyphs with clear, modern text labels.
 */
export function WorkflowStatusBadge({ status, size = 'normal' }) {
  const normStatus = (status || 'UNKNOWN').toUpperCase();

  let statusClass = 'status-pending';
  let label = normStatus;

  switch (normStatus) {
    case 'COMPLETED':
      statusClass = 'status-completed';
      label = 'Completed';
      break;
    case 'RUNNING':
      statusClass = 'status-running';
      label = 'Running';
      break;
    case 'PENDING':
      statusClass = 'status-pending';
      label = 'Pending';
      break;
    case 'WAITING_FOR_APPROVAL':
    case 'AWAITING_APPROVAL':
      statusClass = 'status-waiting';
      label = 'Awaiting Approval';
      break;
    case 'APPROVED':
      statusClass = 'status-approved';
      label = 'Approved';
      break;
    case 'FAILED':
      statusClass = 'status-failed';
      label = 'Failed';
      break;
    case 'CANCELLED':
    case 'REJECTED':
      statusClass = 'status-rejected';
      label = normStatus === 'CANCELLED' ? 'Cancelled' : 'Rejected';
      break;
    case 'CHANGES_REQUESTED':
      statusClass = 'status-changes-requested';
      label = 'Changes Requested';
      break;
    default:
      statusClass = 'status-unknown';
      label = status || 'Unknown';
      break;
  }

  const isSmall = size === 'small';

  return (
    <span className={`status-label ${statusClass} ${isSmall ? 'status-label-sm' : ''}`}>
      <span className="status-bullet" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

export default WorkflowStatusBadge;
