/**
 * Types pour la fonctionnalité de recherche OHADA
 */

export interface SearchMetadata {
  collection?: string;
  title?: string;
  partie?: string;
  chapitre?: string;
  section?: string;
  article?: string;
  document_type?: string;
  [key: string]: string | undefined;
}

export interface Source {
  document_id: string;
  text: string;
  preview: string;
  metadata: SearchMetadata;
  relevance_score: number;
  bm25_score?: number;
  vector_score?: number;
  rerank_score?: number;
}

export interface SearchResponse {
  query: string;
  answer: string;
  sources: Source[];
  search_time: number;
  total_results: number;
  model_used?: string;
}

export interface StreamChunk {
  type: 'progress' | 'text_chunk' | 'sources' | 'complete' | 'error';
  data: any;
}

export interface ProgressEvent {
  status: 'analyzing' | 'retrieving' | 'generating';
  completion: number;
  message?: string;
}

export interface SearchOptions {
  n_results?: number;
  collection_name?: string;
  partie?: number;
  rerank?: boolean;
  include_sources?: boolean;
}

export interface SearchFilters {
  partie?: string;
  chapitre?: string;
  document_type?: string;
}

export interface Suggestion {
  text: string;
  count: number;
  category?: string;
}
