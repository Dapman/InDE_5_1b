/**
 * MilestoneNarrative Component
 *
 * InDE MVP v4.5.0 — The Engagement Engine
 *
 * Displays achievement narratives when artifacts are finalized.
 * Shows a celebratory message with forward-leaning next hint.
 */

import { useState, useEffect } from 'react';
import { Award, ArrowRight, X } from 'lucide-react';
import { cn } from '../../lib/utils';

/**
 * Main MilestoneNarrative component
 */
export function MilestoneNarrative({
  milestone,
  onDismiss,
  onNavigateNext,
  className = ''
}) {
  const [isVisible, setIsVisible] = useState(false);

  // Animate in on mount
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  if (!milestone) {
    return null;
  }

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => onDismiss?.(), 300);
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg border transition-all duration-300",
        "bg-gradient-to-r from-emerald-500/10 via-inde-500/10 to-emerald-500/10",
        "border-emerald-500/30",
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2",
        className
      )}
    >
      {/* Animated background shimmer */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-shimmer" />

      <div className="relative p-4">
        {/* Dismiss button */}
        <button
          onClick={handleDismiss}
          className="absolute top-2 right-2 p-1 hover:bg-surface-3 rounded transition-colors"
        >
          <X className="h-4 w-4 text-zinc-500" />
        </button>

        {/* Achievement badge */}
        <div className="flex items-center gap-2 mb-3">
          <div className="p-1.5 bg-emerald-500/20 rounded-full">
            <Award className="h-4 w-4 text-emerald-400" />
          </div>
          <span className="text-caption text-emerald-400 font-medium">
            Milestone Achieved
          </span>
        </div>

        {/* Headline */}
        <h4 className="text-body font-medium text-zinc-100 mb-2">
          {milestone.headline}
        </h4>

        {/* Narrative */}
        <p className="text-body-sm text-zinc-300 mb-4">
          {milestone.narrative}
        </p>

        {/* Next hint with action */}
        <div className="flex items-center justify-between">
          <p className="text-caption text-zinc-400 italic">
            {milestone.next_hint}
          </p>
          {onNavigateNext && (
            <button
              onClick={() => onNavigateNext(milestone.artifact_type)}
              className={cn(
                "flex items-center gap-1 px-3 py-1.5",
                "bg-inde-500 hover:bg-inde-600 text-white",
                "text-caption font-medium rounded-md transition-colors"
              )}
            >
              <span>Continue</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default MilestoneNarrative;
