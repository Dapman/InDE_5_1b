/**
 * InDE v4.6.0 - Outcome Readiness Tab
 *
 * Admin-only component displaying outcome readiness tracking
 * for all active pursuits. Shows aggregate statistics and
 * per-archetype breakdowns.
 *
 * Features:
 * - Summary bar with total counts and state distribution
 * - Per-archetype readiness breakdown
 * - Average readiness scores by archetype
 * - Auto-refresh every 60 seconds
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  RefreshCw,
  AlertTriangle,
  Target,
  TrendingUp,
  CheckCircle,
  Circle,
  BarChart2,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// =============================================================================
// STATE COLORS AND LABELS
// =============================================================================

const STATE_CONFIG = {
  UNTRACKED: {
    color: 'bg-zinc-500',
    textColor: 'text-zinc-400',
    bgColor: 'bg-zinc-500/10',
    label: 'Not Started',
  },
  EMERGING: {
    color: 'bg-blue-500',
    textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    label: 'Taking Shape',
  },
  PARTIAL: {
    color: 'bg-amber-500',
    textColor: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    label: 'In Progress',
  },
  SUBSTANTIAL: {
    color: 'bg-teal-500',
    textColor: 'text-teal-400',
    bgColor: 'bg-teal-500/10',
    label: 'Nearly Complete',
  },
  READY: {
    color: 'bg-green-500',
    textColor: 'text-green-400',
    bgColor: 'bg-green-500/10',
    label: 'Ready',
  },
};

const ARCHETYPE_LABELS = {
  lean_startup: 'Lean Startup',
  design_thinking: 'Design Thinking',
  stage_gate: 'Stage-Gate',
  triz: 'TRIZ',
  blue_ocean: 'Blue Ocean',
  incubation: 'Incubation',
};

// =============================================================================
// SUMMARY BAR
// =============================================================================

function SummaryBar({ summary, computedAt, onRefresh, isRefreshing }) {
  const getTimeSince = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  return (
    <div className="bg-surface-3 border border-surface-border rounded-lg p-4 mb-4">
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-inde-400" />
          <span className="text-body-md text-zinc-200">
            Pursuits Tracked: <strong>{summary?.total_pursuits_tracked || 0}</strong>
          </span>
          <span className="text-body-sm text-zinc-500 ml-2">
            ({summary?.pursuits_with_ready_artifacts || 0} with ready artifacts)
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-caption text-zinc-500">
            Last updated: {getTimeSince(computedAt)}
          </span>
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 rounded-md bg-surface-4 hover:bg-surface-border transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4 text-zinc-400', isRefreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* State counts */}
      <div className="flex flex-wrap items-center gap-4">
        {Object.entries(STATE_CONFIG).map(([state, config]) => {
          const count = summary?.artifacts_by_state?.[state] || 0;
          return (
            <div key={state} className="flex items-center gap-2">
              <span className={cn('w-2.5 h-2.5 rounded-full', config.color)} />
              <span className={cn('text-body-sm', config.textColor)}>
                {config.label}
              </span>
              <span className="text-body-sm text-zinc-300 font-medium">
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// STATE BADGE
// =============================================================================

function StateBadge({ state }) {
  const config = STATE_CONFIG[state] || STATE_CONFIG.UNTRACKED;

  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-caption font-medium',
      config.bgColor,
      config.textColor
    )}>
      {config.label}
    </span>
  );
}

// =============================================================================
// STAT CARD
// =============================================================================

function StatCard({ label, value, sublabel, icon: Icon }) {
  return (
    <div className="bg-surface-3 border border-surface-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-caption text-zinc-500">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-zinc-500" />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-heading-lg text-zinc-100">{value}</span>
      </div>
      {sublabel && <span className="text-caption text-zinc-600">{sublabel}</span>}
    </div>
  );
}

// =============================================================================
// ARCHETYPE CARD
// =============================================================================

function ArchetypeCard({ archetype }) {
  const label = ARCHETYPE_LABELS[archetype.archetype] || archetype.archetype;
  const readinessPercent = Math.round((archetype.avg_readiness_score || 0) * 100);

  return (
    <div className="bg-surface-3 border border-surface-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-body-md font-medium text-zinc-200">{label}</span>
        <span className={cn(
          'px-2 py-0.5 rounded text-caption font-medium',
          readinessPercent >= 80 ? 'bg-green-500/10 text-green-400' :
          readinessPercent >= 50 ? 'bg-teal-500/10 text-teal-400' :
          readinessPercent >= 25 ? 'bg-amber-500/10 text-amber-400' :
          'bg-zinc-500/10 text-zinc-400'
        )}>
          {readinessPercent}% avg
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-caption">
          <span className="text-zinc-500">Pursuits tracked</span>
          <span className="text-zinc-300">{archetype.pursuits_tracked || 0}</span>
        </div>
        <div className="flex items-center justify-between text-caption">
          <span className="text-zinc-500">With ready artifacts</span>
          <span className="text-zinc-300">{archetype.pursuits_with_ready || 0}</span>
        </div>
      </div>

      {/* Readiness bar */}
      <div className="mt-3">
        <div className="h-2 bg-surface-4 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              readinessPercent >= 80 ? 'bg-green-500' :
              readinessPercent >= 50 ? 'bg-teal-500' :
              readinessPercent >= 25 ? 'bg-amber-500' :
              'bg-zinc-500'
            )}
            style={{ width: `${readinessPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function OutcomeReadinessTab() {
  // Data fetching with auto-refresh
  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['outcome-readiness-summary'],
    queryFn: async () => {
      const response = await fetch('/api/v1/admin/outcome-readiness/summary', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch outcome readiness');
      }
      return response.json();
    },
    refetchInterval: 60000, // 1 minute
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-5 h-5 animate-spin text-zinc-500" />
        <span className="ml-2 text-zinc-500">Loading outcome readiness...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>Failed to load outcome readiness data</span>
        </div>
        <p className="text-caption text-red-400/80 mt-1">
          {error.message}
        </p>
      </div>
    );
  }

  // Handle case when no data yet
  if (!data || data.total_pursuits_tracked === 0) {
    return (
      <div className="space-y-4">
        <SummaryBar
          summary={data}
          computedAt={data?.computed_at}
          onRefresh={refetch}
          isRefreshing={isFetching}
        />

        <div className="text-center py-12 text-zinc-500">
          <Target className="w-10 h-10 mx-auto mb-3 opacity-50" />
          <p className="text-body-md">No outcome readiness data yet</p>
          <p className="text-caption mt-1">
            Data will appear as innovators progress through coaching
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Bar */}
      <SummaryBar
        summary={data}
        computedAt={data?.computed_at}
        onRefresh={refetch}
        isRefreshing={isFetching}
      />

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Tracked"
          value={data?.total_pursuits_tracked || 0}
          sublabel="Pursuits"
          icon={Target}
        />
        <StatCard
          label="With Ready Artifacts"
          value={data?.pursuits_with_ready_artifacts || 0}
          sublabel="Pursuits"
          icon={CheckCircle}
        />
        <StatCard
          label="Field Captures (7d)"
          value={data?.field_capture_rate_7d || 0}
          sublabel="Last 7 days"
          icon={TrendingUp}
        />
        <StatCard
          label="State Transitions (7d)"
          value={data?.state_transitions_7d || 0}
          sublabel="Last 7 days"
          icon={BarChart2}
        />
      </div>

      {/* State Distribution */}
      <div className="bg-surface-2 border border-surface-border rounded-lg p-6">
        <h3 className="text-body-md font-medium text-zinc-200 mb-4">
          Artifact State Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(STATE_CONFIG).map(([state, config]) => {
            const count = data?.artifacts_by_state?.[state] || 0;
            const total = Object.values(data?.artifacts_by_state || {}).reduce((a, b) => a + b, 0);
            const percentage = total > 0 ? (count / total) * 100 : 0;

            return (
              <div key={state} className="flex items-center gap-3">
                <span className={cn('w-24 text-body-sm', config.textColor)}>
                  {config.label}
                </span>
                <div className="flex-1 h-3 bg-surface-4 rounded-full overflow-hidden">
                  <div
                    className={cn('h-full rounded-full transition-all', config.color)}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-body-sm text-zinc-400 w-20 text-right">
                  {count} ({percentage.toFixed(0)}%)
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* By Archetype */}
      {data?.by_archetype && data.by_archetype.length > 0 && (
        <div>
          <h3 className="text-body-md font-medium text-zinc-200 mb-4">
            Readiness by Archetype
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.by_archetype.map((archetype) => (
              <ArchetypeCard key={archetype.archetype} archetype={archetype} />
            ))}
          </div>
        </div>
      )}

      {/* Info Note */}
      <div className="bg-surface-3 border border-surface-border rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Circle className="w-4 h-4 text-inde-400 mt-0.5" />
          <div>
            <p className="text-body-sm text-zinc-300">
              Outcome Readiness is tracked silently in the background
            </p>
            <p className="text-caption text-zinc-500 mt-1">
              Innovators will see their outcome readiness data in v4.7 as part of the
              pursuit completion experience. This view is admin-only for monitoring.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
