/**
 * InDE v5.1.0 - IRC Canvas Display Panel
 *
 * Displays the full .irc canvas with resources organized by phase and category.
 * Uses innovator-facing display labels (Language Sovereignty compliant).
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import ResourceEntryCard from './ResourceEntryCard';

const CanvasDisplayPanel = ({ pursuitId }) => {
  const { authFetch } = useAuth();
  const [canvas, setCanvas] = useState(null);
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('phase'); // 'phase' or 'category'

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // Fetch canvas and resources in parallel
        const [canvasRes, resourcesRes] = await Promise.all([
          authFetch(`/api/pursuits/${pursuitId}/irc/canvas`),
          authFetch(`/api/pursuits/${pursuitId}/irc/resources`),
        ]);

        if (canvasRes.ok) {
          const canvasData = await canvasRes.json();
          setCanvas(canvasData);
        } else if (canvasRes.status !== 404) {
          throw new Error('Failed to load canvas');
        }

        if (resourcesRes.ok) {
          const resourcesData = await resourcesRes.json();
          setResources(resourcesData);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (pursuitId) {
      fetchData();
    }
  }, [pursuitId, authFetch]);

  if (loading) {
    return (
      <div className="canvas-panel canvas-panel-loading">
        <div className="canvas-spinner" />
        <span>Loading resource picture...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="canvas-panel canvas-panel-error">
        <span>Unable to load resource data</span>
      </div>
    );
  }

  if (resources.length === 0) {
    return (
      <div className="canvas-panel canvas-panel-empty">
        <div className="empty-icon">📋</div>
        <h3>No Resources Yet</h3>
        <p>
          As you discuss what you'll need with your coach, resources will appear here.
          Talk about people, tools, data, services, or funding you'll need.
        </p>
      </div>
    );
  }

  // Group resources by phase
  const resourcesByPhase = {
    'Getting Started': [],
    'Testing & Validation': [],
    'Building & Launching': [],
    'Throughout': [],
  };

  // Group resources by category
  const resourcesByCategory = {
    'People & Expertise': [],
    'Tools & Equipment': [],
    'Data & Knowledge': [],
    'External Services': [],
    'Funding & Capital': [],
  };

  const phaseMap = {
    PITCH: 'Getting Started',
    DE_RISK: 'Testing & Validation',
    DEPLOY: 'Building & Launching',
    ACROSS_ALL: 'Throughout',
  };

  const categoryMap = {
    HUMAN_CAPITAL: 'People & Expertise',
    CAPITAL_EQUIPMENT: 'Tools & Equipment',
    DATA_AND_IP: 'Data & Knowledge',
    SERVICES: 'External Services',
    FINANCIAL: 'Funding & Capital',
  };

  resources.forEach(r => {
    // Group by phase
    const phases = r.phase_alignment || ['ACROSS_ALL'];
    phases.forEach(p => {
      const phaseLabel = phaseMap[p] || 'Throughout';
      if (resourcesByPhase[phaseLabel]) {
        resourcesByPhase[phaseLabel].push(r);
      }
    });

    // Group by category
    const catLabel = categoryMap[r.category] || 'External Services';
    if (resourcesByCategory[catLabel]) {
      resourcesByCategory[catLabel].push(r);
    }
  });

  // Format cost display
  const formatCostRange = (low, high) => {
    if (!low && !high) return 'TBD';
    if (low === high) return `$${low?.toLocaleString()}`;
    return `$${low?.toLocaleString() || 0} - $${high?.toLocaleString() || 0}`;
  };

  return (
    <div className="canvas-panel">
      <div className="canvas-header">
        <div className="canvas-title">
          <h2>Resource Picture</h2>
          {canvas && (
            <span className="canvas-completeness">
              {Math.round(canvas.canvas_completeness * 100)}% complete
            </span>
          )}
        </div>

        <div className="view-toggle">
          <button
            className={`view-btn ${viewMode === 'phase' ? 'active' : ''}`}
            onClick={() => setViewMode('phase')}
          >
            By Phase
          </button>
          <button
            className={`view-btn ${viewMode === 'category' ? 'active' : ''}`}
            onClick={() => setViewMode('category')}
          >
            By Category
          </button>
        </div>
      </div>

      {canvas && canvas.coach_synthesis_notes && (
        <div className="canvas-synthesis">
          <p>{canvas.coach_synthesis_notes}</p>
        </div>
      )}

      <div className="canvas-summary">
        <div className="summary-item">
          <span className="summary-value">{resources.length}</span>
          <span className="summary-label">Resources</span>
        </div>
        <div className="summary-item summary-secured">
          <span className="summary-value">{canvas?.secured_count || 0}</span>
          <span className="summary-label">In Place</span>
        </div>
        <div className="summary-item summary-open">
          <span className="summary-value">{canvas?.unresolved_count || 0}</span>
          <span className="summary-label">Still Open</span>
        </div>
        <div className="summary-item summary-cost">
          <span className="summary-value">
            {formatCostRange(canvas?.total_cost_low, canvas?.total_cost_high)}
          </span>
          <span className="summary-label">Est. Cost</span>
        </div>
      </div>

      <div className="canvas-content">
        {viewMode === 'phase' && (
          Object.entries(resourcesByPhase).map(([phase, phaseResources]) => {
            if (phaseResources.length === 0) return null;
            return (
              <div key={phase} className="resource-group">
                <h3 className="group-title">{phase}</h3>
                {phaseResources.map(r => (
                  <ResourceEntryCard key={r.artifact_id} resource={r} compact />
                ))}
              </div>
            );
          })
        )}

        {viewMode === 'category' && (
          Object.entries(resourcesByCategory).map(([category, catResources]) => {
            if (catResources.length === 0) return null;
            return (
              <div key={category} className="resource-group">
                <h3 className="group-title">{category}</h3>
                {catResources.map(r => (
                  <ResourceEntryCard key={r.artifact_id} resource={r} compact />
                ))}
              </div>
            );
          })
        )}
      </div>

      <style jsx>{`
        .canvas-panel {
          padding: 24px;
          background: var(--color-background);
          border-radius: 12px;
        }

        .canvas-panel-loading,
        .canvas-panel-error,
        .canvas-panel-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 300px;
          text-align: center;
          color: var(--color-text-secondary);
        }

        .canvas-spinner {
          width: 32px;
          height: 32px;
          border: 3px solid var(--color-border);
          border-top-color: var(--color-primary);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 12px;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .empty-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }

        .canvas-panel-empty h3 {
          font-size: 18px;
          color: var(--color-text-primary);
          margin-bottom: 8px;
        }

        .canvas-panel-empty p {
          max-width: 400px;
          line-height: 1.5;
        }

        .canvas-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .canvas-title {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .canvas-title h2 {
          font-size: 20px;
          font-weight: 600;
          color: var(--color-text-primary);
          margin: 0;
        }

        .canvas-completeness {
          padding: 4px 10px;
          background: var(--color-primary-light);
          color: var(--color-primary);
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .view-toggle {
          display: flex;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 6px;
          overflow: hidden;
        }

        .view-btn {
          padding: 8px 16px;
          border: none;
          background: none;
          font-size: 13px;
          color: var(--color-text-secondary);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .view-btn:hover {
          color: var(--color-text-primary);
        }

        .view-btn.active {
          background: var(--color-primary);
          color: white;
        }

        .canvas-synthesis {
          padding: 16px;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 8px;
          margin-bottom: 20px;
        }

        .canvas-synthesis p {
          margin: 0;
          font-size: 14px;
          line-height: 1.6;
          color: var(--color-text-primary);
        }

        .canvas-summary {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
          margin-bottom: 24px;
        }

        .summary-item {
          padding: 16px;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 8px;
          text-align: center;
        }

        .summary-value {
          display: block;
          font-size: 24px;
          font-weight: 600;
          color: var(--color-text-primary);
        }

        .summary-label {
          font-size: 12px;
          color: var(--color-text-tertiary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .summary-secured .summary-value {
          color: var(--color-success);
        }

        .summary-open .summary-value {
          color: var(--color-warning);
        }

        .resource-group {
          margin-bottom: 24px;
        }

        .group-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--color-text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--color-border);
        }
      `}</style>
    </div>
  );
};

export default CanvasDisplayPanel;
