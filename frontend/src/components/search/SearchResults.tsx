import React from 'react';
import { SourceCard } from './SourceCard';
import type { Source } from '@/features/search/types';
import { FileSearch } from 'lucide-react';

interface SearchResultsProps {
  sources: Source[];
  isLoading?: boolean;
}

export function SearchResults({ sources, isLoading }: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Sources</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 bg-secondary animate-pulse rounded-lg"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FileSearch className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-lg font-semibold text-foreground">
          Sources ({sources.length})
        </h2>
      </div>
      <div className="grid grid-cols-1 gap-3">
        {sources.map((source, index) => (
          <SourceCard key={source.document_id || index} source={source} index={index} />
        ))}
      </div>
    </div>
  );
}
