/**
 * ExportPanel Component
 *
 * InDE MVP v4.5.0 — The Engagement Engine
 *
 * Displays export options below finalized artifacts:
 * - Download PDF
 * - Create Share Link
 * - Copy as Text
 *
 * Only appears for finalized artifacts (has content).
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Download,
  Link,
  Copy,
  Check,
  Loader2,
  Eye,
  Clock,
  X
} from 'lucide-react';
import { cn } from '../../lib/utils';
import client from '../../api/client';

/**
 * Export an artifact
 */
async function exportArtifact(pursuitId, artifactType, format, expiryDays = 7) {
  const response = await client.post(
    `/v1/pursuits/${pursuitId}/artifacts/${artifactType}/export`,
    { format, expiry_days: expiryDays },
    { responseType: format === 'pdf' ? 'blob' : 'json' }
  );
  return response.data;
}

/**
 * Get share analytics for a pursuit
 */
async function getShareAnalytics(pursuitId) {
  const response = await client.get(`/v1/pursuits/${pursuitId}/share-analytics`);
  return response.data;
}

/**
 * Small action button component
 */
function ActionButton({ icon: Icon, label, onClick, loading, success, disabled, className }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 text-caption rounded-md",
        "transition-colors",
        disabled ? "opacity-50 cursor-not-allowed" : "hover:bg-surface-3",
        success ? "text-health-optimal" : "text-zinc-400",
        className
      )}
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : success ? (
        <Check className="h-3.5 w-3.5" />
      ) : (
        <Icon className="h-3.5 w-3.5" />
      )}
      <span>{label}</span>
    </button>
  );
}

/**
 * Share link display with view count
 */
function ShareLinkDisplay({ url, viewCount, onClose }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-2 p-2 bg-surface-1 rounded-md border border-surface-border">
      <div className="flex items-center justify-between mb-1">
        <span className="text-caption text-zinc-500">Share link created</span>
        <button onClick={onClose} className="p-0.5 hover:bg-surface-3 rounded">
          <X className="h-3 w-3 text-zinc-500" />
        </button>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={url}
          readOnly
          className="flex-1 text-caption bg-surface-2 border border-surface-border rounded px-2 py-1 text-zinc-300"
        />
        <button
          onClick={handleCopy}
          className="p-1.5 hover:bg-surface-3 rounded transition-colors"
          title="Copy link"
        >
          {copied ? (
            <Check className="h-4 w-4 text-health-optimal" />
          ) : (
            <Copy className="h-4 w-4 text-zinc-400" />
          )}
        </button>
      </div>
      {viewCount !== undefined && (
        <div className="flex items-center gap-1 mt-1.5 text-caption text-zinc-500">
          <Eye className="h-3 w-3" />
          <span>{viewCount} view{viewCount !== 1 ? 's' : ''}</span>
        </div>
      )}
    </div>
  );
}

/**
 * Main ExportPanel component
 */
export function ExportPanel({
  pursuitId,
  artifactType,
  hasContent = true,
  className = ''
}) {
  const queryClient = useQueryClient();
  const [shareLink, setShareLink] = useState(null);
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(false);

  // Get existing share links for this pursuit
  const { data: analytics } = useQuery({
    queryKey: ['share-analytics', pursuitId],
    queryFn: () => getShareAnalytics(pursuitId),
    enabled: !!pursuitId,
    staleTime: 30000,
  });

  // Find existing link for this artifact type
  const existingLink = analytics?.links?.find(
    link => link.artifact_type === artifactType
  );

  // PDF export mutation
  const pdfMutation = useMutation({
    mutationFn: () => exportArtifact(pursuitId, artifactType, 'pdf'),
    onSuccess: (blob) => {
      // Download the PDF
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${artifactType}_export.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setPdfSuccess(true);
      setTimeout(() => setPdfSuccess(false), 2000);
    }
  });

  // Share link mutation
  const linkMutation = useMutation({
    mutationFn: () => exportArtifact(pursuitId, artifactType, 'link'),
    onSuccess: (data) => {
      setShareLink({ url: data.url, viewCount: 0 });
      queryClient.invalidateQueries(['share-analytics', pursuitId]);
    }
  });

  // Markdown copy mutation
  const markdownMutation = useMutation({
    mutationFn: () => exportArtifact(pursuitId, artifactType, 'markdown'),
    onSuccess: async (data) => {
      await navigator.clipboard.writeText(data.markdown);
      setCopiedMarkdown(true);
      setTimeout(() => setCopiedMarkdown(false), 2000);
    }
  });

  if (!hasContent) {
    return null;
  }

  return (
    <div className={cn("border-t border-surface-border pt-3 mt-3", className)}>
      <div className="flex items-center gap-1">
        <ActionButton
          icon={Download}
          label="PDF"
          onClick={() => pdfMutation.mutate()}
          loading={pdfMutation.isPending}
          success={pdfSuccess}
        />
        <ActionButton
          icon={Link}
          label={existingLink ? `Share (${existingLink.view_count} views)` : "Share"}
          onClick={() => linkMutation.mutate()}
          loading={linkMutation.isPending}
          success={!!shareLink}
        />
        <ActionButton
          icon={Copy}
          label="Copy"
          onClick={() => markdownMutation.mutate()}
          loading={markdownMutation.isPending}
          success={copiedMarkdown}
        />
      </div>

      {shareLink && (
        <ShareLinkDisplay
          url={shareLink.url}
          viewCount={shareLink.viewCount}
          onClose={() => setShareLink(null)}
        />
      )}

      {existingLink && !shareLink && (
        <div className="mt-2 flex items-center gap-2 text-caption text-zinc-500">
          <Link className="h-3 w-3" />
          <span>Existing link: {existingLink.view_count} views</span>
          <Clock className="h-3 w-3 ml-2" />
          <span>Expires {new Date(existingLink.expires_at).toLocaleDateString()}</span>
        </div>
      )}
    </div>
  );
}

export default ExportPanel;
