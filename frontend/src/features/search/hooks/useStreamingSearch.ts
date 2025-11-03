import { useState, useCallback, useRef } from 'react';
import type { Source, ProgressEvent, SearchOptions } from '../types';

interface StreamingState {
  isStreaming: boolean;
  answer: string;
  sources: Source[];
  progress: ProgressEvent | null;
  error: string | null;
}

/**
 * Hook pour effectuer une recherche en streaming (SSE)
 */
export const useStreamingSearch = () => {
  const [state, setState] = useState<StreamingState>({
    isStreaming: false,
    answer: '',
    sources: [],
    progress: null,
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const search = useCallback(async (query: string, options?: SearchOptions) => {
    // Reset state
    setState({
      isStreaming: true,
      answer: '',
      sources: [],
      progress: { status: 'analyzing', completion: 0 },
      error: null,
    });

    try {
      // Construct URL with query parameters
      const baseUrl = import.meta.env.VITE_API_URL || '/api';
      const params = new URLSearchParams({
        query,
        n_results: String(options?.n_results || 5),
        include_sources: String(options?.include_sources ?? true),
      });

      if (options?.collection_name) {
        params.append('collection_name', options.collection_name);
      }
      if (options?.partie) {
        params.append('partie', String(options.partie));
      }
      if (options?.rerank !== undefined) {
        params.append('rerank', String(options.rerank));
      }

      const url = `${baseUrl}/stream?${params.toString()}`;

      // Create EventSource
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      // Handle progress events
      eventSource.addEventListener('progress', (e) => {
        try {
          const data: ProgressEvent = JSON.parse(e.data);
          setState((prev) => ({ ...prev, progress: data }));
        } catch (err) {
          console.error('Error parsing progress event:', err);
        }
      });

      // Handle text chunks
      eventSource.addEventListener('chunk', (e) => {
        try {
          const data = JSON.parse(e.data);
          setState((prev) => ({
            ...prev,
            answer: prev.answer + data.text,
          }));
        } catch (err) {
          console.error('Error parsing chunk event:', err);
        }
      });

      // Handle sources
      eventSource.addEventListener('sources', (e) => {
        try {
          const data = JSON.parse(e.data);
          setState((prev) => ({
            ...prev,
            sources: data.sources || [],
          }));
        } catch (err) {
          console.error('Error parsing sources event:', err);
        }
      });

      // Handle completion
      eventSource.addEventListener('complete', (e) => {
        try {
          const data = JSON.parse(e.data);
          setState((prev) => ({
            ...prev,
            isStreaming: false,
            answer: data.answer || prev.answer,
            sources: data.sources || prev.sources,
            progress: { status: 'generating', completion: 100 },
          }));
          eventSource.close();
        } catch (err) {
          console.error('Error parsing complete event:', err);
          setState((prev) => ({ ...prev, isStreaming: false }));
          eventSource.close();
        }
      });

      // Handle errors
      eventSource.addEventListener('error', (e) => {
        console.error('EventSource error:', e);
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: 'Erreur lors de la recherche. Veuillez réessayer.',
        }));
        eventSource.close();
      });

      // Handle generic error (connection failure)
      eventSource.onerror = () => {
        console.error('EventSource connection error');
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: 'Impossible de se connecter au serveur. Veuillez vérifier votre connexion.',
        }));
        eventSource.close();
      };
    } catch (error) {
      console.error('Error starting streaming search:', error);
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        error: 'Erreur lors du démarrage de la recherche.',
      }));
    }
  }, []);

  const cancel = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setState((prev) => ({ ...prev, isStreaming: false }));
    }
  }, []);

  const reset = useCallback(() => {
    cancel();
    setState({
      isStreaming: false,
      answer: '',
      sources: [],
      progress: null,
      error: null,
    });
  }, [cancel]);

  return {
    ...state,
    search,
    cancel,
    reset,
  };
};
