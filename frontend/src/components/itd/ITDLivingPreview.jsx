/**
 * InDE v4.8 - ITD Living Preview Component
 *
 * Displays real-time ITD layer readiness during an active pursuit.
 * Shows the innovator how their Innovation Thesis is forming.
 *
 * Features:
 * - Six-layer readiness bar (color-coded by status)
 * - Overall readiness score (natural language, not percentage for novices)
 * - Coach message about current progress
 * - Expandable detail view showing data signals per layer
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import { useState, useEffect } from "react";
import { useExperienceMode } from "../../contexts/ExperienceContext";
import "./ITDLivingPreview.css";

const LAYER_LABELS = {
  thesis_statement: {
    novice: "Your Core Insight",
    expert: "Thesis Statement",
  },
  evidence_architecture: {
    novice: "What You Discovered",
    expert: "Evidence Architecture",
  },
  narrative_arc: {
    novice: "Your Story",
    expert: "Narrative Arc",
  },
  coachs_perspective: {
    novice: "Key Moments",
    expert: "Coach's Perspective",
  },
  pattern_connections: {
    novice: "The Bigger Picture",
    expert: "Pattern Connections",
  },
  forward_projection: {
    novice: "What Comes Next",
    expert: "Forward Projection",
  },
};

const STATUS_CONFIG = {
  NOT_STARTED: { color: "var(--color-neutral-400)", label: "Not yet begun" },
  FORMING:     { color: "var(--color-amber-500)",   label: "Taking shape"  },
  READY:       { color: "var(--color-blue-500)",    label: "Ready"         },
  COMPLETE:    { color: "var(--color-green-500)",   label: "Complete"      },
};

export default function ITDLivingPreview({ pursuitId }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const { isExpertMode } = useExperienceMode?.() || { isExpertMode: false };

  useEffect(() => {
    if (!pursuitId) return;

    setLoading(true);
    setError(null);

    fetch(`/api/v1/pursuits/${pursuitId}/itd/preview`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load preview");
        return r.json();
      })
      .then((data) => {
        setPreview(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [pursuitId]);

  if (loading) {
    return (
      <div className="itd-living-preview itd-living-preview--loading">
        <div className="itd-preview-skeleton" />
      </div>
    );
  }

  if (error || !preview) {
    return null; // Silent failure - don't block the UI
  }

  const overallPct = Math.round(preview.overall_readiness * 100);
  const isCompleted = preview.preview_type === "COMPLETED";

  const getOverallReadinessLabel = (pct) => {
    if (pct < 20) return "Beginning to form";
    if (pct < 40) return "Foundation building";
    if (pct < 60) return "Taking shape";
    if (pct < 80) return "Well developed";
    if (pct < 95) return "Nearly complete";
    return "Ready";
  };

  const getLayerLabel = (layerKey) => {
    const labels = LAYER_LABELS[layerKey] || { novice: layerKey, expert: layerKey };
    return isExpertMode ? labels.expert : labels.novice;
  };

  return (
    <div
      className={`itd-living-preview ${isCompleted ? "itd-living-preview--completed" : ""}`}
      aria-label="Innovation Thesis Preview"
    >
      {/* Header */}
      <div
        className="itd-preview-header"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => e.key === "Enter" && setExpanded(!expanded)}
      >
        <span className="itd-preview-title">
          {isExpertMode ? "Innovation Thesis" : "Your Thesis"}
        </span>
        <span className="itd-preview-readiness">
          {isCompleted ? "Complete" : getOverallReadinessLabel(overallPct)}
        </span>
        <span className="itd-preview-chevron">{expanded ? "\u25B2" : "\u25BC"}</span>
      </div>

      {/* Overall progress bar */}
      <div className="itd-preview-progress-bar">
        <div
          className="itd-preview-progress-fill"
          style={{
            width: `${overallPct}%`,
            backgroundColor: isCompleted
              ? "var(--color-green-500)"
              : overallPct > 70
              ? "var(--color-blue-500)"
              : "var(--color-amber-500)",
          }}
          role="progressbar"
          aria-valuenow={overallPct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* Expanded detail view */}
      {expanded && (
        <div className="itd-preview-layers">
          {preview.layers.map((layer) => {
            const statusConfig = STATUS_CONFIG[layer.status] || STATUS_CONFIG.NOT_STARTED;

            return (
              <div
                key={layer.layer_key}
                className={`itd-preview-layer itd-preview-layer--${layer.status.toLowerCase()}`}
              >
                <div className="itd-preview-layer-header">
                  <span className="itd-preview-layer-number">{layer.layer_number}</span>
                  <span className="itd-preview-layer-name">
                    {getLayerLabel(layer.layer_key)}
                  </span>
                  <span
                    className="itd-preview-layer-status"
                    style={{ color: statusConfig.color }}
                  >
                    {layer.display_label || statusConfig.label}
                  </span>
                </div>

                {/* Layer progress bar */}
                <div className="itd-preview-layer-bar">
                  <div
                    className="itd-preview-layer-fill"
                    style={{
                      width: `${Math.round(layer.score * 100)}%`,
                      backgroundColor: statusConfig.color,
                    }}
                  />
                </div>

                {/* Data signals */}
                {layer.data_signals && layer.data_signals.length > 0 && (
                  <div className="itd-preview-layer-signals">
                    {layer.data_signals.map((signal, idx) => (
                      <span key={idx} className="itd-preview-signal">
                        {signal}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Coach message */}
      {preview.coach_message && (
        <div className="itd-preview-coach-message">
          <span className="itd-preview-coach-icon">{"\u{1F4A1}"}</span>
          <p>{preview.coach_message}</p>
        </div>
      )}

      {/* What is this? tooltip for novices */}
      {!isExpertMode && !isCompleted && (
        <div className="itd-preview-tooltip">
          <details>
            <summary>What is this?</summary>
            <p>
              As you work through your pursuit, I'm assembling an Innovation Thesis
              that captures your full journey - your insights, discoveries, key moments,
              and what they mean for your path forward. This preview shows how that
              document is forming.
            </p>
          </details>
        </div>
      )}
    </div>
  );
}
