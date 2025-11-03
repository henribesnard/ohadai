/**
 * Hook pour gérer les conversations
 */
import { useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { conversationsService } from '../services/conversationsService';
import type { Conversation, ConversationCreate, MessageCreate, MessageResponse } from '../types';

export function useConversations() {
  const queryClient = useQueryClient();

  // Récupérer toutes les conversations
  const {
    data: conversations = [],
    isLoading: isLoadingConversations,
    error: conversationsError,
    refetch: refetchConversations,
  } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsService.getConversations(),
  });

  // Créer une nouvelle conversation
  const createConversationMutation = useMutation({
    mutationFn: (data: ConversationCreate) => conversationsService.createConversation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  // Supprimer une conversation
  const deleteConversationMutation = useMutation({
    mutationFn: (conversationId: string) => conversationsService.deleteConversation(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  // Envoyer un message
  const sendMessageMutation = useMutation({
    mutationFn: ({ conversationId, content }: { conversationId: string; content: string }) =>
      conversationsService.sendMessage(conversationId, content),
    onSuccess: (_, variables) => {
      // Invalider la conversation pour recharger les messages
      queryClient.invalidateQueries({ queryKey: ['conversation', variables.conversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  // Créer un message (peut créer une nouvelle conversation)
  const createMessageMutation = useMutation({
    mutationFn: (data: MessageCreate) => conversationsService.createMessage(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  return {
    conversations,
    isLoadingConversations,
    conversationsError,
    refetchConversations,
    createConversation: createConversationMutation.mutateAsync,
    isCreatingConversation: createConversationMutation.isPending,
    deleteConversation: deleteConversationMutation.mutateAsync,
    isDeletingConversation: deleteConversationMutation.isPending,
    sendMessage: sendMessageMutation.mutateAsync,
    isSendingMessage: sendMessageMutation.isPending,
    createMessage: createMessageMutation.mutateAsync,
    isCreatingMessage: createMessageMutation.isPending,
  };
}

export function useConversation(conversationId: string | null) {
  const queryClient = useQueryClient();

  // Récupérer une conversation spécifique
  const {
    data: conversation,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => conversationsService.getConversation(conversationId!),
    enabled: !!conversationId,
  });

  // Mettre à jour le titre de la conversation
  const updateConversationMutation = useMutation({
    mutationFn: ({ title }: { title: string }) =>
      conversationsService.updateConversation(conversationId!, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  return {
    conversation,
    isLoading,
    error,
    refetch,
    updateConversation: updateConversationMutation.mutateAsync,
    isUpdating: updateConversationMutation.isPending,
  };
}
