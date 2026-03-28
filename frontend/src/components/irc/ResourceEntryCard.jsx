/**
 * InDE v5.1.0 - Resource Entry Card Component
 *
 * Displays a single .resource entry in the canvas view.
 * Uses innovator-facing display labels (Language Sovereignty compliant).
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import React, { useState } from 'react';

// Display label mappings (Language Sovereignty compliant)
const CATEGORY_LABELS = {
  HUMAN_CAPITAL: 'People & Expertise',
  CAPITAL_EQUIPMENT: 'Tools & Equipment',
  DATA_AND_IP: 'Data & Knowledge',
  SERVICES: 'External Services',
  FINANCIAL: 'Funding & Capital',
};

const AVAILABILITY_LABELS = {
  SECURED: 'In Place',
  IN_DISCUSSION: 'Being Arranged',
  UNRESOLVED: 'Still Open',
  UNKNOWN: 'Not Yet Explored',
};

const AVAILABILITY_COLORS = {
  SECURED: 'var(--color-success)',
  IN_DISCUSSION: 'var(--color-primary)',
  UNRESOLVED: 'var(--color-warning)',
  UNKNOWN: 'var(--color-neutral-400)',
};

const CRITICALITY_LABELS = {
  ESSENTIAL: 'Essential',
  IMPORTANT: 'Important',
  HELPFUL: 'Helpful',
  UNKNOWN: 'To Be Assessed',
};

const ResourceEntryCard = ({ resource, onUpdate, compact = false }) => {
  const [expanded, setExpanded] = useState(false);

  const categoryLabel = CATEGORY_LABELS[resource.category] || resource.category;
  const availabilityLabel = AVAILABILITY_LABELS[resource.availability_status] || resource.availability_status;
  const availabilityColor = AVAILABILITY_COLORS[resource.availability_status] || 'var(--color-neutral-400)';
  const criticalityLabel = CRITICALITY_LABELS[resource.criticality] || resource.criticality;

  // Format cost display
  const formatCost = () => {
    const low = resource.cost_estimate_low;
    const high = resource.cost_estimate_high;

    if (low === null && high === null) return 'TBD';
    if (low === high && low !== null) return `$${low.toLocaleString()}`;
    if (low !== null && high !== null) return `$${low.toLocaleString()} - $${high.toLocaleString()}`;
    if (low !== null) return `$${low.toLocaleString()}+`;
    if (high !== null) return `Up to $${high.toLocaleString()}`;
    return 'TBD';
  };

  if (compact) {
    return (
      <div className="resource-card resource-card-compact">
        <div className="resource-card-header">
          <span
            className="resource-status-dot"
            style={{ backgroundColor: availabilityColor }}
            title={availabilityLabel}
          />
          <span className="resource-name">{resource.resource_name}</span>
        </div>
        <div className="resource-card-meta">
          <span className="resource-category">{categoryLabel}</span>
          <span className="resource-cost">{formatCost()}</span>
        </div>

        <style jsx>{`
          .resource-card-compact {
            padding: 8px 12px;
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 6px;
            margin-bottom: 8px;
          }

          .resource-card-header {
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .resource-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
          }

          .resource-name {
            font-size: 13px;
            font-weight: 500;
            color: var(--color-text-primary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .resource-card-meta {
            display: flex;
            justify-content: space-between;
            margin-top: 4px;
            padding-left: 16px;
            font-size: 11px;
            color: var(--color-text-tertiary);
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="resource-card">
      <div className="resource-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="resource-header-left">
          <span
            className="resource-status-badge"
            style={{ backgroundColor: availabilityColor }}
          >
            {availabilityLabel}
          </span>
          <span className="resource-name">{resource.resource_name}</span>
        </div>
        <button className="resource-expand-btn">
          {expanded ? '▼' : '▶'}
        </button>
      </div>

      <div className="resource-card-summary">
        <span className="resource-category">{categoryLabel}</span>
        <span className="resource-divider">•</span>
        <span className="resource-cost">{formatCost()}</span>
        {resource.criticality !== 'UNKNOWN' && (
          <>
            <span className="resource-divider">•</span>
            <span className="resource-criticality">{criticalityLabel}</span>
          </>
        )}
      </div>

      {expanded && (
        <div className="resource-card-details">
          {resource.availability_notes && (
            <div className="resource-detail-row">
              <span className="detail-label">Notes</span>
              <span className="detail-value">{resource.availability_notes}</span>
            </div>
          )}

          {resource.duration_description && (
            <div className="resource-detail-row">
              <span className="detail-label">Duration</span>
              <span className="detail-value">{resource.duration_description}</span>
            </div>
          )}

          {resource.phase_alignment && resource.phase_alignment.length > 0 && (
            <div className="resource-detail-row">
              <span className="detail-label">Phase</span>
              <span className="detail-value">
                {resource.phase_alignment.map(p => {
                  if (p === 'PITCH') return 'Getting Started';
                  if (p === 'DE_RISK') return 'Testing & Validation';
                  if (p === 'DEPLOY') return 'Building & Launching';
                  if (p === 'ACROSS_ALL') return 'Throughout';
                  return p;
                }).join(', ')}
              </span>
            </div>
          )}

          {resource.challenge_registered && (
            <div className="resource-challenge-note">
              There are some open questions around this resource
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .resource-card {
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 8px;
          margin-bottom: 12px;
          overflow: hidden;
        }

        .resource-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          cursor: pointer;
        }

        .resource-card-header:hover {
          background: var(--color-surface-hover);
        }

        .resource-header-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .resource-status-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          color: white;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .resource-name {
          font-size: 15px;
          font-weight: 600;
          color: var(--color-text-primary);
        }

        .resource-expand-btn {
          background: none;
          border: none;
          color: var(--color-text-tertiary);
          cursor: pointer;
          font-size: 10px;
          padding: 4px;
        }

        .resource-card-summary {
          padding: 0 16px 12px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: var(--color-text-secondary);
        }

        .resource-divider {
          color: var(--color-border);
        }

        .resource-card-details {
          border-top: 1px solid var(--color-border);
          padding: 12px 16px;
          background: var(--color-surface-secondary);
        }

        .resource-detail-row {
          display: flex;
          margin-bottom: 8px;
        }

        .resource-detail-row:last-child {
          margin-bottom: 0;
        }

        .detail-label {
          width: 100px;
          font-size: 12px;
          color: var(--color-text-tertiary);
          flex-shrink: 0;
        }

        .detail-value {
          font-size: 13px;
          color: var(--color-text-primary);
        }

        .resource-challenge-note {
          margin-top: 12px;
          padding: 8px 12px;
          background: var(--color-warning-light);
          border-radius: 4px;
          font-size: 12px;
          color: var(--color-warning-dark);
        }
      `}</style>
    </div>
  );
};

export default ResourceEntryCard;
