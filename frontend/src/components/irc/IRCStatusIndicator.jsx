/**
 * InDE v5.1.0 - IRC Status Indicator Component
 *
 * Displays the current IRC status in the pursuit sidebar.
 * Uses innovator-facing display labels (Language Sovereignty compliant).
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';

const IRCStatusIndicator = ({ pursuitId }) => {
  const { authFetch } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setLoading(true);
        const response = await authFetch(`/api/pursuits/${pursuitId}/irc/status`);

        if (response.ok) {
          const data = await response.json();
          setStatus(data);
        } else if (response.status === 404) {
          // No IRC data yet - show empty state
          setStatus({
            has_canvas: false,
            resource_count: 0,
            status_label: 'No resources yet',
            status_description: 'Resources will appear as you discuss what you\'ll need',
          });
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (pursuitId) {
      fetchStatus();
    }
  }, [pursuitId, authFetch]);

  if (loading) {
    return (
      <div className="irc-status-indicator irc-status-loading">
        <div className="irc-status-spinner" />
      </div>
    );
  }

  if (error) {
    return null; // Fail silently - IRC is optional
  }

  if (!status) {
    return null;
  }

  // Determine status color
  const getStatusColor = () => {
    if (status.resource_count === 0) return 'var(--color-neutral-400)';
    if (status.canvas_completeness >= 0.8) return 'var(--color-success)';
    if (status.canvas_completeness >= 0.5) return 'var(--color-primary)';
    return 'var(--color-warning)';
  };

  // Determine icon
  const getStatusIcon = () => {
    if (status.resource_count === 0) return '📋';
    if (status.has_canvas && status.canvas_completeness >= 0.8) return '✓';
    if (status.has_canvas) return '📊';
    return '📝';
  };

  return (
    <div className="irc-status-indicator">
      <div className="irc-status-header">
        <span
          className="irc-status-icon"
          style={{ backgroundColor: getStatusColor() }}
        >
          {getStatusIcon()}
        </span>
        <span className="irc-status-label">{status.status_label}</span>
      </div>

      <div className="irc-status-detail">
        {status.status_description}
      </div>

      {status.resource_count > 0 && (
        <div className="irc-status-metrics">
          <span className="irc-metric">
            {status.resource_count} resource{status.resource_count !== 1 ? 's' : ''}
          </span>
          {status.secured_count > 0 && (
            <span className="irc-metric irc-metric-secured">
              {status.secured_count} in place
            </span>
          )}
          {status.unresolved_count > 0 && (
            <span className="irc-metric irc-metric-open">
              {status.unresolved_count} open
            </span>
          )}
        </div>
      )}

      {status.has_canvas && (
        <div className="irc-completeness-bar">
          <div
            className="irc-completeness-fill"
            style={{
              width: `${Math.round(status.canvas_completeness * 100)}%`,
              backgroundColor: getStatusColor(),
            }}
          />
        </div>
      )}

      <style jsx>{`
        .irc-status-indicator {
          padding: 12px;
          background: var(--color-surface);
          border-radius: 8px;
          border: 1px solid var(--color-border);
          margin-bottom: 16px;
        }

        .irc-status-loading {
          display: flex;
          justify-content: center;
          padding: 20px;
        }

        .irc-status-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid var(--color-border);
          border-top-color: var(--color-primary);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .irc-status-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }

        .irc-status-icon {
          width: 24px;
          height: 24px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          color: white;
        }

        .irc-status-label {
          font-weight: 600;
          font-size: 14px;
          color: var(--color-text-primary);
        }

        .irc-status-detail {
          font-size: 12px;
          color: var(--color-text-secondary);
          margin-bottom: 8px;
        }

        .irc-status-metrics {
          display: flex;
          gap: 12px;
          font-size: 11px;
        }

        .irc-metric {
          color: var(--color-text-tertiary);
        }

        .irc-metric-secured {
          color: var(--color-success);
        }

        .irc-metric-open {
          color: var(--color-warning);
        }

        .irc-completeness-bar {
          height: 4px;
          background: var(--color-neutral-200);
          border-radius: 2px;
          margin-top: 8px;
          overflow: hidden;
        }

        .irc-completeness-fill {
          height: 100%;
          transition: width 0.3s ease;
        }
      `}</style>
    </div>
  );
};

export default IRCStatusIndicator;
