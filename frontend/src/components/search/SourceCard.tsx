import React from 'react';
import { Card } from '@/components/ui/card';
import type { Source } from '@/features/search/types';
import { FileText } from 'lucide-react';

interface SourceCardProps {
  source: Source;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
  const { metadata, preview, relevance_score, rerank_score } = source;

  // Use rerank_score if available, otherwise use relevance_score
  const displayScore = rerank_score !== undefined ? rerank_score : relevance_score;

  // Convert score to percentage (handle negative rerank scores)
  const scorePercentage = rerank_score !== undefined
    ? Math.max(0, Math.min(100, (1 + rerank_score) * 50)) // Convert [-1, 1] to [0, 100]
    : displayScore * 100;

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        {/* Source number badge */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-sm">
          {index + 1}
        </div>

        <div className="flex-1 min-w-0">
          {/* Header: Title and Score */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <h3 className="font-semibold text-sm truncate">
                {metadata.title || 'Document OHADA'}
              </h3>
            </div>
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {scorePercentage.toFixed(0)}%
            </span>
          </div>

          {/* Metadata */}
          {(metadata.partie || metadata.chapitre || metadata.collection) && (
            <div className="flex flex-wrap gap-2 mb-2">
              {metadata.collection && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-secondary text-secondary-foreground">
                  {metadata.collection}
                </span>
              )}
              {metadata.partie && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-accent text-accent-foreground">
                  Partie {metadata.partie}
                </span>
              )}
              {metadata.chapitre && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-accent text-accent-foreground">
                  Chapitre {metadata.chapitre}
                </span>
              )}
            </div>
          )}

          {/* Preview text */}
          <p className="text-sm text-foreground/80 line-clamp-3">
            {preview || source.text}
          </p>
        </div>
      </div>
    </Card>
  );
}
