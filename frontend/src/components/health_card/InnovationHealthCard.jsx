/**
 * Innovation Health Card Component
 *
 * InDE MVP v4.5.0 — The Engagement Engine
 *
 * Displays an organic, depth-framed visualization of how developed an idea is
 * across five growth dimensions: Clarity, Resilience, Evidence, Direction, Momentum.
 *
 * Adapts to user experience level:
 * - Novice: Growth icon + summary only
 * - Intermediate: + dimension labels with descriptions
 * - Expert: + numeric scores
 */

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../stores/authStore';
import {
  Sprout,
  Trees,
  TreeDeciduous,
  Eye,
  Shield,
  FlaskConical,
  Compass,
  Zap,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '../../lib/utils';
import client from '../../api/client';

// Growth stage icons
const STAGE_ICONS = {
  seed: Sprout,
  roots: Sprout,
  stem: TreeDeciduous,
  branches: Trees,
  canopy: Trees,
};

// Dimension icons
const DIMENSION_ICONS = {
  clarity: Eye,
  resilience: Shield,
  evidence: FlaskConical,
  direction: Compass,
  momentum: Zap,
};

/**
 * Fetch health card data for a pursuit
 */
async function fetchHealthCard(pursuitId) {
  const response = await client.get(`/v1/pursuits/${pursuitId}/health-card`);
  return response.data;
}

/**
 * Single dimension bar (for intermediate/expert modes)
 */
function DimensionBar({ dimension, showScore = false }) {
  const Icon = DIMENSION_ICONS[dimension.key] || Eye;
  const percentage = Math.round(dimension.score * 100);

  return (
    <div className="flex items-center gap-2 py-1.5">
      <Icon
        className="h-4 w-4 flex-shrink-0"
        style={{ color: dimension.color }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-caption text-zinc-300 truncate">
            {dimension.label}
          </span>
          {showScore && (
            <span className="text-caption text-zinc-500 ml-2">
              {percentage}%
            </span>
          )}
        </div>
        <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${percentage}%`,
              backgroundColor: dimension.color
            }}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Growth stage visual (center icon with stage label)
 */
function GrowthStageVisual({ stage, stageLabel, accent }) {
  const Icon = STAGE_ICONS[stage] || Sprout;

  return (
    <div className="flex flex-col items-center py-4">
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center mb-3"
        style={{ backgroundColor: `${accent}20` }}
      >
        <Icon
          className="h-8 w-8"
          style={{ color: accent }}
        />
      </div>
      <p className="text-body-sm text-zinc-300 text-center">
        {stageLabel}
      </p>
    </div>
  );
}

/**
 * Main Innovation Health Card component
 */
export function InnovationHealthCard({
  pursuitId,
  className = '',
  defaultExpanded = true
}) {
  const user = useAuthStore((s) => s.user);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Determine experience mode
  const experienceMode = user?.preferences?.experience_mode || 'novice';
  const showDimensions = experienceMode !== 'novice';
  const showScores = experienceMode === 'expert';

  // Fetch health card data
  const { data: healthCard, isLoading, error } = useQuery({
    queryKey: ['health-card', pursuitId],
    queryFn: () => fetchHealthCard(pursuitId),
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 60000,
  });

  // Loading state
  if (isLoading) {
    return (
      <div className={cn("bg-surface-2 rounded-lg border border-surface-border p-4", className)}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-surface-3 rounded w-1/3 mx-auto" />
          <div className="h-16 w-16 bg-surface-3 rounded-full mx-auto" />
          <div className="h-3 bg-surface-3 rounded w-2/3 mx-auto" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return null; // Silently fail — don't block other panel content
  }

  // No data
  if (!healthCard) {
    return null;
  }

  return (
    <div
      className={cn(
        "bg-surface-2 rounded-lg border border-surface-border overflow-hidden",
        "transition-all duration-300",
        className
      )}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-3/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Sprout className="h-4 w-4 text-inde-400" />
          <span className="text-body-sm font-medium text-zinc-200">
            Innovation Health
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-zinc-500" />
        ) : (
          <ChevronRight className="h-4 w-4 text-zinc-500" />
        )}
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Growth stage visual */}
          <GrowthStageVisual
            stage={healthCard.growth_stage}
            stageLabel={healthCard.growth_stage_label}
            accent={healthCard.growth_stage_accent}
          />

          {/* Summary */}
          <p className="text-caption text-zinc-400 text-center">
            {healthCard.summary}
          </p>

          {/* Dimensions (intermediate/expert only) */}
          {showDimensions && healthCard.dimensions && (
            <div className="space-y-1 pt-2 border-t border-surface-border">
              {healthCard.dimensions.map((dimension) => (
                <DimensionBar
                  key={dimension.key}
                  dimension={dimension}
                  showScore={showScores}
                />
              ))}
            </div>
          )}

          {/* Next hint */}
          <div className="pt-3 border-t border-surface-border">
            <p className="text-caption text-inde-400 text-center italic">
              {healthCard.next_hint}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default InnovationHealthCard;
