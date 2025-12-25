import { apiClient } from '../../services/api';

export interface Collection {
  id: number;
  name: string;
  description: string;
  created_by: number;
  created_at: string;
  is_public: boolean;
  embedding_provider: string;
  embedding_model: string;
}

export interface ChunkResult {
  chunk_id: number;
  text: string;
  chunk_index: number;
  provider: string;
  model: string;
  filename: string;
  file_type: string;
  collection: string;
  score: number;
}

export interface RAGTestRequest {
  query: string;
  collection_id?: number;
  top_k?: number;
  score_threshold?: number;
  search_method?: string;
  embedding_provider?: string;
  embedding_model?: string;
  include_metadata?: boolean;
}

export interface RAGTestResponse {
  success: boolean;
  chunks: ChunkResult[];
  context: string;
  total_retrieved: number;
  query_used: string;
}

export const ragService = {
  /**
   * Get available collections
   */
  getCollections: async (): Promise<{ collections: Collection[] }> => {
    return apiClient.get<{ collections: Collection[] }>('/rag/collections');
  },

  /**
   * Get a specific collection by ID
   */
  getCollection: async (collectionId: number): Promise<Collection> => {
    return apiClient.get<Collection>(`/rag/collections/${collectionId}`);
  },

  /**
   * Test RAG retrieval
   */
  testRetrieval: async (
    request: RAGTestRequest
  ): Promise<RAGTestResponse> => {
    return apiClient.post<RAGTestResponse>('/rag/test', request);
  },
};
