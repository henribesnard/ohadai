import React from 'react';
import { Card } from '@/components/ui/card';
import type { ProgressEvent } from '@/features/search/types';
import { Loader2 } from 'lucide-react';

interface StreamingAnswerProps {
  answer: string;
  isStreaming: boolean;
  progress: ProgressEvent | null;
  error: string | null;
}

const getStatusMessage = (status: ProgressEvent['status']): string => {
  switch (status) {
    case 'analyzing':
      return 'Analyse de votre question...';
    case 'retrieving':
      return 'Recherche dans les documents OHADA...';
    case 'generating':
      return 'Génération de la réponse...';
    default:
      return 'En cours...';
  }
};

export function StreamingAnswer({
  answer,
  isStreaming,
  progress,
  error,
}: StreamingAnswerProps) {
  if (error) {
    return (
      <Card className="p-6 border-destructive">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-destructive/10 flex items-center justify-center">
            <span className="text-destructive text-lg">!</span>
          </div>
          <div>
            <h3 className="font-semibold text-destructive mb-1">Erreur</h3>
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      {progress && isStreaming && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              {getStatusMessage(progress.status)}
            </span>
            <span className="text-muted-foreground font-medium">
              {Math.round(progress.completion * 100)}%
            </span>
          </div>
          <div className="h-1 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${progress.completion * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Answer text */}
      {answer && (
        <Card className="p-6">
          <div className="prose prose-slate max-w-none">
            <div className="whitespace-pre-wrap text-foreground">
              {answer}
              {isStreaming && (
                <span className="inline-block w-2 h-5 ml-1 bg-primary animate-pulse" />
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
