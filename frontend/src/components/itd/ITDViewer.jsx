/**
 * InDE v4.8 - ITD Viewer Component
 *
 * Displays the complete Innovation Thesis Document with all six layers.
 *
 * Layer Architecture:
 * 1. Thesis Statement - Core innovation narrative synthesis
 * 2. Evidence Architecture - Confidence trajectory and pivot record
 * 3. Narrative Arc - Archetype-structured story in 5 acts
 * 4. Coach's Perspective - Curated coaching moments
 * 5. Pattern Connections - IML/IKF influence map (NEW in v4.8)
 * 6. Forward Projection - 90/180/365-day trajectory analysis (NEW in v4.8)
 *
 * Plus: Methodology Transparency section (expert-gated, NEW in v4.8)
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import { useState, useEffect } from "react";
import { useExperienceMode } from "../../contexts/ExperienceContext";
import "./ITDViewer.css";

// Layer display configuration
const LAYER_CONFIG = {
  thesis_statement: {
    number: 1,
    title: "Your Innovation Thesis",
    noviceTitle: "Your Core Insight",
    icon: "\u{1F4DC}",
  },
  evidence_architecture: {
    number: 2,
    title: "Evidence Architecture",
    noviceTitle: "What You Discovered",
    icon: "\u{1F4CA}",
  },
  narrative_arc: {
    number: 3,
    title: "Narrative Arc",
    noviceTitle: "Your Story",
    icon: "\u{1F4D6}",
  },
  coachs_perspective: {
    number: 4,
    title: "Coach's Perspective",
    noviceTitle: "Key Moments",
    icon: "\u{1F4AC}",
  },
  pattern_connections: {
    number: 5,
    title: "Pattern Connections",
    noviceTitle: "The Bigger Picture",
    icon: "\u{1F517}",
  },
  forward_projection: {
    number: 6,
    title: "Forward Projection",
    noviceTitle: "What Comes Next",
    icon: "\u{1F52E}",
  },
};

export default function ITDViewer({ pursuitId, itdId }) {
  const [itd, setItd] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedLayers, setExpandedLayers] = useState(new Set([1, 2, 3, 4, 5, 6]));
  const [showTransparency, setShowTransparency] = useState(false);
  const { isExpertMode, experienceLevel } = useExperienceMode?.() || {
    isExpertMode: false,
    experienceLevel: "NOVICE"
  };

  useEffect(() => {
    if (!pursuitId) return;

    setLoading(true);
    setError(null);

    const url = itdId
      ? `/api/v1/itd/${itdId}`
      : `/api/v1/pursuits/${pursuitId}/itd`;

    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load Innovation Thesis");
        return r.json();
      })
      .then((data) => {
        setItd(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [pursuitId, itdId]);

  const toggleLayer = (layerNumber) => {
    setExpandedLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layerNumber)) {
        next.delete(layerNumber);
      } else {
        next.add(layerNumber);
      }
      return next;
    });
  };

  const getLayerTitle = (key) => {
    const config = LAYER_CONFIG[key];
    if (!config) return key;
    return isExpertMode ? config.title : config.noviceTitle;
  };

  if (loading) {
    return (
      <div className="itd-viewer itd-viewer--loading">
        <div className="itd-viewer-skeleton" />
        <p>Loading your Innovation Thesis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="itd-viewer itd-viewer--error">
        <p>Unable to load Innovation Thesis: {error}</p>
      </div>
    );
  }

  if (!itd) return null;

  // Check if methodology transparency is available and user is eligible
  const showMethodologyTransparency = itd.methodology_transparency &&
    (experienceLevel === "EXPERT" || experienceLevel === "ADVANCED");

  return (
    <div className="itd-viewer">
      {/* Header */}
      <header className="itd-viewer-header">
        <h1>{itd.pursuit_title || "Innovation Thesis Document"}</h1>
        <p className="itd-viewer-meta">
          Generated {new Date(itd.created_at).toLocaleDateString()}
          {itd.composition_version && ` \u2022 v${itd.composition_version}`}
        </p>
      </header>

      {/* Layer 1: Thesis Statement */}
      {itd.thesis_statement && (
        <LayerSection
          config={LAYER_CONFIG.thesis_statement}
          expanded={expandedLayers.has(1)}
          onToggle={() => toggleLayer(1)}
          isExpertMode={isExpertMode}
        >
          <div className="itd-thesis-content">
            <p className="itd-thesis-text">{itd.thesis_statement.thesis_text}</p>
            {isExpertMode && itd.thesis_statement.confidence_score > 0 && (
              <span className="itd-confidence-badge">
                Confidence: {Math.round(itd.thesis_statement.confidence_score * 100)}%
              </span>
            )}
          </div>
        </LayerSection>
      )}

      {/* Layer 2: Evidence Architecture */}
      {itd.evidence_architecture && (
        <LayerSection
          config={LAYER_CONFIG.evidence_architecture}
          expanded={expandedLayers.has(2)}
          onToggle={() => toggleLayer(2)}
          isExpertMode={isExpertMode}
        >
          <EvidenceArchitectureContent
            layer={itd.evidence_architecture}
            isExpertMode={isExpertMode}
          />
        </LayerSection>
      )}

      {/* Layer 3: Narrative Arc */}
      {itd.narrative_arc && (
        <LayerSection
          config={LAYER_CONFIG.narrative_arc}
          expanded={expandedLayers.has(3)}
          onToggle={() => toggleLayer(3)}
          isExpertMode={isExpertMode}
        >
          <NarrativeArcContent
            layer={itd.narrative_arc}
            isExpertMode={isExpertMode}
          />
        </LayerSection>
      )}

      {/* Layer 4: Coach's Perspective */}
      {itd.coachs_perspective && (
        <LayerSection
          config={LAYER_CONFIG.coachs_perspective}
          expanded={expandedLayers.has(4)}
          onToggle={() => toggleLayer(4)}
          isExpertMode={isExpertMode}
        >
          <CoachsPerspectiveContent
            layer={itd.coachs_perspective}
            isExpertMode={isExpertMode}
          />
        </LayerSection>
      )}

      {/* Layer 5: Pattern Connections (NEW in v4.8) */}
      {itd.pattern_connections && (
        <LayerSection
          config={LAYER_CONFIG.pattern_connections}
          expanded={expandedLayers.has(5)}
          onToggle={() => toggleLayer(5)}
          isExpertMode={isExpertMode}
        >
          <PatternConnectionsContent
            layer={itd.pattern_connections}
            isExpertMode={isExpertMode}
          />
        </LayerSection>
      )}

      {/* Layer 6: Forward Projection (NEW in v4.8) */}
      {itd.forward_projection && (
        <LayerSection
          config={LAYER_CONFIG.forward_projection}
          expanded={expandedLayers.has(6)}
          onToggle={() => toggleLayer(6)}
          isExpertMode={isExpertMode}
        >
          <ForwardProjectionContent
            layer={itd.forward_projection}
            isExpertMode={isExpertMode}
          />
        </LayerSection>
      )}

      {/* Methodology Transparency (Expert-Gated, NEW in v4.8) */}
      {showMethodologyTransparency && (
        <div className="itd-methodology-transparency">
          <button
            className="itd-transparency-toggle"
            onClick={() => setShowTransparency(!showTransparency)}
            aria-expanded={showTransparency}
          >
            <span>{"\u{1F50D}"} Coaching Pattern Provenance</span>
            <span className="itd-transparency-chevron">
              {showTransparency ? "\u25B2" : "\u25BC"}
            </span>
          </button>
          {showTransparency && (
            <MethodologyTransparencyContent
              section={itd.methodology_transparency}
            />
          )}
        </div>
      )}
    </div>
  );
}

// Layer Section Component
function LayerSection({ config, expanded, onToggle, isExpertMode, children }) {
  return (
    <section className={`itd-layer itd-layer--${expanded ? "expanded" : "collapsed"}`}>
      <header
        className="itd-layer-header"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => e.key === "Enter" && onToggle()}
      >
        <span className="itd-layer-number">{config.number}</span>
        <span className="itd-layer-icon">{config.icon}</span>
        <h2 className="itd-layer-title">
          {isExpertMode ? config.title : config.noviceTitle}
        </h2>
        <span className="itd-layer-chevron">{expanded ? "\u25B2" : "\u25BC"}</span>
      </header>
      {expanded && <div className="itd-layer-content">{children}</div>}
    </section>
  );
}

// Evidence Architecture Content
function EvidenceArchitectureContent({ layer, isExpertMode }) {
  return (
    <div className="itd-evidence">
      {layer.confidence_trajectory && layer.confidence_trajectory.length > 0 && (
        <div className="itd-evidence-trajectory">
          <h3>Confidence Journey</h3>
          <div className="itd-evidence-stats">
            <span>Started: {Math.round((layer.initial_confidence || 0) * 100)}%</span>
            <span>Ended: {Math.round((layer.final_confidence || 0) * 100)}%</span>
            <span>
              Change: {layer.confidence_delta > 0 ? "+" : ""}
              {Math.round((layer.confidence_delta || 0) * 100)}%
            </span>
          </div>
        </div>
      )}
      {layer.pivots && layer.pivots.length > 0 && (
        <div className="itd-evidence-pivots">
          <h3>Direction Changes</h3>
          {layer.pivots.map((pivot, idx) => (
            <div key={idx} className="itd-pivot-item">
              <span className="itd-pivot-type">{pivot.pivot_type}</span>
              <p>{pivot.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Narrative Arc Content
function NarrativeArcContent({ layer, isExpertMode }) {
  const ACT_LABELS = {
    inception: "The Beginning",
    exploration: "Discovery",
    validation: "Testing",
    synthesis: "Understanding",
    resolution: "The Outcome",
  };

  return (
    <div className="itd-narrative">
      {layer.opening_hook && (
        <p className="itd-narrative-opening">{layer.opening_hook}</p>
      )}
      {layer.acts && layer.acts.map((act, idx) => (
        <div key={idx} className="itd-narrative-act">
          <h3>{ACT_LABELS[act.act_type] || act.title}</h3>
          <p>{act.content}</p>
        </div>
      ))}
      {layer.closing_reflection && (
        <p className="itd-narrative-closing">{layer.closing_reflection}</p>
      )}
    </div>
  );
}

// Coach's Perspective Content
function CoachsPerspectiveContent({ layer, isExpertMode }) {
  return (
    <div className="itd-coach">
      {layer.overall_reflection && (
        <p className="itd-coach-reflection">{layer.overall_reflection}</p>
      )}
      {layer.moments && layer.moments.map((moment, idx) => (
        <div key={idx} className="itd-coach-moment">
          <span className="itd-moment-type">{moment.moment_type}</span>
          <blockquote>{moment.coach_quote}</blockquote>
          {moment.impact && <p className="itd-moment-impact">{moment.impact}</p>}
        </div>
      ))}
    </div>
  );
}

// Pattern Connections Content (NEW in v4.8)
function PatternConnectionsContent({ layer, isExpertMode }) {
  const content = layer.content || layer;

  return (
    <div className="itd-pattern-connections">
      {content.opening && (
        <p className="itd-pattern-opening">{content.opening}</p>
      )}

      {content.within_pursuit && content.within_pursuit.narrative && (
        <div className="itd-pattern-section">
          <h3>Within This Pursuit</h3>
          <p>{content.within_pursuit.narrative}</p>
          {isExpertMode && content.within_pursuit.pattern_count > 0 && (
            <span className="itd-pattern-count">
              {content.within_pursuit.pattern_count} pattern(s) applied
            </span>
          )}
        </div>
      )}

      {content.cross_pursuit && content.cross_pursuit.narrative && (
        <div className="itd-pattern-section">
          <h3>Connections to Other Pursuits</h3>
          <p>{content.cross_pursuit.narrative}</p>
        </div>
      )}

      {content.federation && content.federation.narrative && (
        <div className="itd-pattern-section">
          <h3>Cross-Organization Intelligence</h3>
          <p>{content.federation.narrative}</p>
        </div>
      )}

      {content.synthesis && (
        <p className="itd-pattern-synthesis">{content.synthesis}</p>
      )}
    </div>
  );
}

// Forward Projection Content (NEW in v4.8)
function ForwardProjectionContent({ layer, isExpertMode }) {
  const content = layer.content || layer;

  const HORIZON_LABELS = {
    day_90: "90-Day Horizon",
    day_180: "180-Day Horizon",
    day_365: "One-Year Horizon",
  };

  return (
    <div className="itd-forward-projection">
      {content.synthesis_statement && (
        <p className="itd-projection-synthesis">{content.synthesis_statement}</p>
      )}

      {content.horizons && (
        <div className="itd-projection-horizons">
          {["day_90", "day_180", "day_365"].map((key) => {
            const horizon = content.horizons[key];
            if (!horizon) return null;

            return (
              <div key={key} className="itd-horizon">
                <h3>{HORIZON_LABELS[key]}</h3>
                <p>{horizon.narrative}</p>
                {isExpertMode && horizon.confidence > 0 && (
                  <span className="itd-horizon-confidence">
                    Confidence: {Math.round(horizon.confidence * 100)}%
                  </span>
                )}
                {horizon.success_correlated_actions &&
                  horizon.success_correlated_actions.length > 0 && (
                    <div className="itd-horizon-actions">
                      <h4>Actions associated with positive outcomes:</h4>
                      <ul>
                        {horizon.success_correlated_actions.map((action, idx) => (
                          <li key={idx}>{action}</li>
                        ))}
                      </ul>
                    </div>
                  )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Methodology Transparency Content (Expert-Gated, NEW in v4.8)
function MethodologyTransparencyContent({ section }) {
  const content = section.content || section;

  return (
    <div className="itd-transparency-content">
      {content.orchestration_summary && (
        <p className="itd-transparency-summary">{content.orchestration_summary}</p>
      )}

      {content.methodology_influences &&
        content.methodology_influences.length > 0 && (
          <div className="itd-transparency-influences">
            <h4>Methodology Influences</h4>
            {content.methodology_influences.map((influence, idx) => (
              <div key={idx} className="itd-influence-item">
                <span className="itd-influence-approach">
                  {influence.approach_description}
                </span>
                <span className="itd-influence-where">
                  Applied: {influence.where_applied}
                </span>
                <span className="itd-influence-why">
                  Why: {influence.why_selected}
                </span>
              </div>
            ))}
          </div>
        )}

      {content.blending_notes && (
        <p className="itd-transparency-blending">
          <strong>Blending:</strong> {content.blending_notes}
        </p>
      )}

      {content.adaptation_narrative && (
        <p className="itd-transparency-adaptation">
          <strong>Adaptation:</strong> {content.adaptation_narrative}
        </p>
      )}
    </div>
  );
}
