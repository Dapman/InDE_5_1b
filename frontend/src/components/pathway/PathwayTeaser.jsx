/**
 * PathwayTeaser Component
 *
 * InDE MVP v4.5.0 — The Engagement Engine
 *
 * Displays a forward-leaning teaser for the next coaching pathway
 * after an artifact is finalized. Creates continuity from achievement
 * to next action.
 */

import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, X, Sparkles, MessageCircle, Info } from 'lucide-react';
import { cn } from '../../lib/utils';
import client from '../../api/client';

/**
 * Pathway guidance messages shown when CTA is clicked
 */
const PATHWAY_GUIDANCE = {
  fears: {
    title: "Explore Your Risks",
    message: "Start a coaching conversation and ask about potential risks or challenges to your vision. Your coach will help you identify and document key concerns.",
    prompt: "What risks might threaten my vision?"
  },
  hypothesis: {
    title: "Define Your Hypothesis",
    message: "In your next coaching session, explore the assumptions underlying your idea. Your coach will help you form testable hypotheses.",
    prompt: "What assumptions am I making?"
  },
  validation: {
    title: "Plan Your Validation",
    message: "Discuss validation strategies with your coach. Together you'll design experiments to test your key hypotheses.",
    prompt: "How can I test my hypothesis?"
  },
  retrospective: {
    title: "Reflect on Your Journey",
    message: "Take time to reflect on what you've learned. Your coach can help you capture insights and plan next steps.",
    prompt: "What have I learned from this pursuit?"
  }
};

/**
 * Fetch pathway teaser
 */
async function fetchPathwayTeaser(pursuitId) {
  const response = await client.get(`/v1/pursuits/${pursuitId}/pathway-teaser`);
  return response.data;
}

/**
 * Get localStorage key for dismissed teasers
 */
function getDismissedKey(pursuitId) {
  return `inde-dismissed-teasers-${pursuitId}`;
}

/**
 * Check if a teaser has been dismissed for this pursuit
 */
function isTeaserDismissed(pursuitId, targetPathway) {
  try {
    const dismissed = JSON.parse(localStorage.getItem(getDismissedKey(pursuitId)) || '[]');
    return dismissed.includes(targetPathway);
  } catch {
    return false;
  }
}

/**
 * Mark a teaser as dismissed for this pursuit
 */
function dismissTeaser(pursuitId, targetPathway) {
  try {
    const key = getDismissedKey(pursuitId);
    const dismissed = JSON.parse(localStorage.getItem(key) || '[]');
    if (!dismissed.includes(targetPathway)) {
      dismissed.push(targetPathway);
      localStorage.setItem(key, JSON.stringify(dismissed));
    }
  } catch {
    // Ignore localStorage errors
  }
}

/**
 * Main PathwayTeaser component
 */
export function PathwayTeaser({
  pursuitId,
  onNavigate,
  onTeaserAvailable,
  className = ''
}) {
  const [dismissed, setDismissed] = useState(false);
  const [showGuidance, setShowGuidance] = useState(false);
  const lastTeaserIdRef = useRef(null);

  // Fetch teaser
  const { data: teaser, isLoading } = useQuery({
    queryKey: ['pathway-teaser', pursuitId],
    queryFn: () => fetchPathwayTeaser(pursuitId),
    enabled: !!pursuitId && !dismissed,
    staleTime: 60000,
  });

  // Check if this teaser was previously dismissed (persistent)
  useEffect(() => {
    if (teaser?.target_pathway && isTeaserDismissed(pursuitId, teaser.target_pathway)) {
      setDismissed(true);
    }
  }, [pursuitId, teaser?.target_pathway]);

  // Notify parent when teaser data changes/becomes available
  useEffect(() => {
    if (teaser && !dismissed && onTeaserAvailable) {
      // Only trigger if this is new teaser data
      const teaserId = teaser.id || teaser.target_pathway;
      if (teaserId !== lastTeaserIdRef.current) {
        lastTeaserIdRef.current = teaserId;
        onTeaserAvailable(teaser);
      }
    }
  }, [teaser, dismissed, onTeaserAvailable]);

  // Loading or dismissed
  if (isLoading || dismissed || !teaser) {
    return null;
  }

  const handleNavigate = () => {
    if (onNavigate) {
      onNavigate(teaser.target_pathway);
    } else {
      // Show inline guidance when no navigation handler provided
      setShowGuidance(true);
    }
  };

  // Get guidance content for the target pathway
  const guidance = PATHWAY_GUIDANCE[teaser?.target_pathway] || {
    title: "Continue Your Journey",
    message: "Start a coaching conversation to explore this next step in your innovation journey.",
    prompt: "What should I focus on next?"
  };

  const handleDismiss = () => {
    // Persist dismissal to localStorage
    if (teaser?.target_pathway) {
      dismissTeaser(pursuitId, teaser.target_pathway);
    }
    setDismissed(true);
  };

  return (
    <div
      className={cn(
        "relative p-4 rounded-lg border transition-all",
        "bg-gradient-to-r from-inde-500/10 to-inde-400/5",
        "border-inde-500/20",
        className
      )}
    >
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 p-1 hover:bg-surface-3 rounded transition-colors"
        title="Not now"
      >
        <X className="h-4 w-4 text-zinc-500" />
      </button>

      {/* IML indicator */}
      {teaser.source === 'iml' && (
        <div className="flex items-center gap-1 mb-2 text-caption text-inde-400">
          <Sparkles className="h-3 w-3" />
          <span>Based on community patterns</span>
        </div>
      )}

      {/* Headline */}
      <h4 className="text-body-sm font-medium text-zinc-200 mb-2 pr-6">
        {teaser.headline}
      </h4>

      {/* Body */}
      <p className="text-caption text-zinc-400 mb-3">
        {teaser.body}
      </p>

      {/* Pattern previews (if IML) */}
      {teaser.pattern_previews && teaser.pattern_previews.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {teaser.pattern_previews.slice(0, 2).map((preview, i) => (
            <span
              key={i}
              className="px-2 py-0.5 text-caption bg-surface-3 rounded text-zinc-400"
            >
              {preview}
            </span>
          ))}
        </div>
      )}

      {/* CTA Button or Guidance */}
      {!showGuidance ? (
        <button
          onClick={handleNavigate}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5",
            "bg-inde-500 hover:bg-inde-600 text-white",
            "text-caption font-medium rounded-md transition-colors"
          )}
        >
          <span>{teaser.cta}</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      ) : (
        <div className="p-3 bg-surface-3 rounded-lg border border-surface-border">
          {/* Title row */}
          <div className="flex items-center gap-2 mb-3">
            <Info className="h-4 w-4 text-inde-400" />
            <span className="text-sm font-medium text-zinc-200">
              {guidance.title}
            </span>
          </div>

          {/* Message */}
          <p className="text-sm text-zinc-400 mb-4">
            {guidance.message}
          </p>

          {/* Suggested prompt */}
          <div className="p-2 bg-surface-2 rounded border border-surface-border mb-3">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4 text-inde-400" />
              <span className="text-sm text-zinc-300">
                Try asking: <em>"{guidance.prompt}"</em>
              </span>
            </div>
          </div>

          {/* Back button */}
          <button
            onClick={() => setShowGuidance(false)}
            className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            ← Back
          </button>
        </div>
      )}
    </div>
  );
}

export default PathwayTeaser;
