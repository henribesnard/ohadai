/**
 * Service pour gérer les conversations
 */
import apiClient from '@/lib/api/axios';
import type {
  Conversation,
  ConversationCreate,
  ConversationUpdate,
  MessageCreate,
  MessageResponse,
} from '../types';

export const conversationsService = {
  /**
   * Récupère toutes les conversations de l'utilisateur
   */
  async getConversations(limit: number = 50, offset: number = 0): Promise<Conversation[]> {
    const response = await apiClient.get<Conversation[]>('/conversations/', {
      params: { limit, offset },
    });
    return response.data;
  },

  /**
   * Crée une nouvelle conversation
   */
  async createConversation(data: ConversationCreate): Promise<Conversation> {
    const response = await apiClient.post<Conversation>('/conversations/', data);
    return response.data;
  },

  /**
   * Récupère une conversation spécifique avec ses messages
   */
  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await apiClient.get<Conversation>(`/conversations/${conversationId}`);
    return response.data;
  },

  /**
   * Met à jour le titre d'une conversation
   */
  async updateConversation(
    conversationId: string,
    data: ConversationUpdate
  ): Promise<Conversation> {
    const response = await apiClient.put<Conversation>(`/conversations/${conversationId}`, data);
    return response.data;
  },

  /**
   * Supprime une conversation
   */
  async deleteConversation(conversationId: string): Promise<void> {
    await apiClient.delete(`/conversations/${conversationId}`);
  },

  /**
   * Envoie un message dans une conversation existante
   */
  async sendMessage(conversationId: string, content: string): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>(
      `/conversations/${conversationId}/messages`,
      { content }
    );
    return response.data;
  },

  /**
   * Crée un message (dans une conversation existante ou nouvelle)
   */
  async createMessage(data: MessageCreate): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/conversations/messages', data);
    return response.data;
  },
};
