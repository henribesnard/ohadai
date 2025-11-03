import React from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send, X } from 'lucide-react';
import { useStreamingSearch } from '@/features/search/hooks/useStreamingSearch';
import { StreamingAnswer } from '@/components/search/StreamingAnswer';
import { SearchResults } from '@/components/search/SearchResults';

const exampleQuestions = [
  'Comment comptabiliser les immobilisations corporelles?',
  'Quelles sont les règles d\'amortissement selon SYSCOHADA?',
  'Comment établir un bilan conforme OHADA?',
  'Qu\'est-ce que le plan comptable SYSCOHADA révisé?',
  'Comment comptabiliser les stocks?',
  'Quels sont les états financiers obligatoires?',
];

export function HomePage() {
  const [query, setQuery] = React.useState('');
  const [hasSearched, setHasSearched] = React.useState(false);

  const {
    answer,
    sources,
    isStreaming,
    progress,
    error,
    search,
    reset,
  } = useStreamingSearch();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setHasSearched(true);
      search(query, { n_results: 5, rerank: true });
    }
  };

  const handleQuestionClick = (question: string) => {
    setQuery(question);
    setHasSearched(true);
    search(question, { n_results: 5, rerank: true });
  };

  const handleReset = () => {
    setQuery('');
    setHasSearched(false);
    reset();
  };

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Welcome Header - Only show when no search */}
        {!hasSearched && (
          <>
            <div className="text-center space-y-4 py-12">
              <h1 className="text-4xl font-bold text-foreground">
                Bienvenue sur OHAD'AI
              </h1>
              <p className="text-xl text-muted-foreground">
                Expert en comptabilité OHADA et SYSCOHADA
              </p>
            </div>

            {/* Example Questions Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {exampleQuestions.map((question, index) => (
                <Card
                  key={index}
                  className="p-4 hover:bg-accent transition-colors cursor-pointer"
                  onClick={() => handleQuestionClick(question)}
                >
                  <p className="text-sm text-foreground">{question}</p>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* Search Input */}
        <form onSubmit={handleSubmit} className="relative">
          <Input
            type="text"
            placeholder="Posez votre question sur le plan comptable OHADA..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pr-24 py-6 text-base"
            disabled={isStreaming}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {hasSearched && !isStreaming && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={handleReset}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
            <Button
              type="submit"
              size="icon"
              disabled={!query.trim() || isStreaming}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>

        {/* Search Results */}
        {hasSearched && (
          <div className="space-y-8">
            {/* Streaming Answer */}
            <StreamingAnswer
              answer={answer}
              isStreaming={isStreaming}
              progress={progress}
              error={error}
            />

            {/* Sources */}
            {sources.length > 0 && (
              <SearchResults sources={sources} isLoading={false} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
