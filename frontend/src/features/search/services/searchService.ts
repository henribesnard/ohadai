import apiClient from '@/lib/api/axios';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import type { SearchResponse, SearchOptions, Suggestion } from '../types';

/**
 * Service de recherche pour l'API OHADA
 */

/**
 * Effectue une recherche classique (non-streaming)
 */
export const search = async (
  query: string,
  options?: SearchOptions
): Promise<SearchResponse> => {
  const response = await apiClient.post<SearchResponse>(API_ENDPOINTS.SEARCH.QUERY, {
    query,
    n_results: options?.n_results || 5,
    collection_name: options?.collection_name,
    partie: options?.partie,
    rerank: options?.rerank ?? true,
    include_sources: options?.include_sources ?? true,
  });

  return response.data;
};

/**
 * Récupère des suggestions de recherche
 */
export const getSuggestions = async (query: string): Promise<Suggestion[]> => {
  if (query.length < 3) return [];

  try {
    const response = await apiClient.get<Suggestion[]>(
      `${API_ENDPOINTS.SEARCH.SUGGESTIONS}?query=${encodeURIComponent(query)}`
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching suggestions:', error);
    return [];
  }
};

export const searchService = {
  search,
  getSuggestions,
};
