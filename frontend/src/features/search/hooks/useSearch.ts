import { useQuery } from '@tanstack/react-query';
import { searchService } from '../services/searchService';
import type { SearchOptions, SearchResponse } from '../types';

/**
 * Hook pour effectuer une recherche classique (non-streaming)
 */
export const useSearch = (query: string, options?: SearchOptions) => {
  return useQuery<SearchResponse>({
    queryKey: ['search', query, options],
    queryFn: () => searchService.search(query, options),
    enabled: query.length > 0,
    staleTime: 10 * 60 * 1000, // Cache 10 minutes
    retry: 1,
  });
};

/**
 * Hook pour récupérer des suggestions de recherche
 */
export const useSuggestions = (query: string) => {
  return useQuery({
    queryKey: ['suggestions', query],
    queryFn: () => searchService.getSuggestions(query),
    enabled: query.length >= 3,
    staleTime: 5 * 60 * 1000, // Cache 5 minutes
  });
};
