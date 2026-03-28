/**
 * CohortPulse Component
 *
 * InDE MVP v4.5.0 — The Engagement Engine
 *
 * Displays a subtle ambient indicator of community presence.
 * All metrics are anonymized aggregates — no PII.
 *
 * Respects user preference: cohort_visibility_enabled
 */

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../stores/authStore';
import { Users, Activity, Sparkles, TrendingUp } from 'lucide-react';
import { cn } from '../../lib/utils';
import client from '../../api/client';

// Signal tier styles
const SIGNAL_STYLES = {
  buzzing: {
    icon: Sparkles,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    pulseColor: 'bg-amber-400',
    animate: true,
  },
  active: {
    icon: Activity,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    pulseColor: 'bg-emerald-400',
    animate: true,
  },
  warming_up: {
    icon: TrendingUp,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    pulseColor: 'bg-blue-400',
    animate: false,
  },
  getting_started: {
    icon: Users,
    color: 'text-zinc-400',
    bgColor: 'bg-zinc-500/10',
    pulseColor: 'bg-zinc-400',
    animate: false,
  },
};

/**
 * Fetch cohort signals
 */
async function fetchCohortSignals() {
  const response = await client.get('/v1/cohort/signals');
  return response.data;
}

/**
 * Main CohortPulse component
 */
export function CohortPulse({ className = '' }) {
  const user = useAuthStore((s) => s.user);

  // Check if user has opted out
  const cohortVisible = user?.preferences?.cohort_visibility_enabled !== false;

  // Fetch cohort signals
  const { data: signals, isLoading } = useQuery({
    queryKey: ['cohort-signals'],
    queryFn: fetchCohortSignals,
    enabled: cohortVisible,
    staleTime: 60000,      // 1 minute
    refetchInterval: 300000, // 5 minutes
  });

  // Don't render if user has opted out
  if (!cohortVisible) {
    return null;
  }

  // Loading state
  if (isLoading) {
    return (
      <div className={cn("p-3 bg-surface-2 rounded-lg border border-surface-border", className)}>
        <div className="animate-pulse flex items-center gap-2">
          <div className="h-4 w-4 rounded-full bg-surface-3" />
          <div className="h-3 bg-surface-3 rounded w-32" />
        </div>
      </div>
    );
  }

  // No data
  if (!signals) {
    return null;
  }

  const signalTier = signals.cohort_momentum_signal || 'getting_started';
  const style = SIGNAL_STYLES[signalTier] || SIGNAL_STYLES.getting_started;
  const Icon = style.icon;

  return (
    <div
      className={cn(
        "p-3 rounded-lg border border-surface-border transition-all",
        style.bgColor,
        className
      )}
    >
      <div className="flex items-center gap-2">
        {/* Animated pulse indicator */}
        <div className="relative">
          <Icon className={cn("h-4 w-4", style.color)} />
          {style.animate && (
            <span
              className={cn(
                "absolute inset-0 rounded-full animate-ping opacity-50",
                style.pulseColor
              )}
            />
          )}
        </div>

        {/* Signal label */}
        <span className="text-caption text-zinc-300">
          {signals.signal_label}
        </span>
      </div>

      {/* Metrics row (subtle) */}
      <div className="flex items-center gap-4 mt-2 text-caption text-zinc-500">
        <span>{signals.active_24h} active today</span>
        <span>{signals.artifacts_7d} artifacts this week</span>
      </div>
    </div>
  );
}

export default CohortPulse;
