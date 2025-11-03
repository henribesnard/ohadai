/**
 * Composant pour afficher une conversation complète avec ses messages
 */
import React, { useRef, useEffect } from 'react';
import type { Conversation } from '@/features/conversations/types';
import { ChatMessage } from './ChatMessage';
import { Loader2 } from 'lucide-react';

interface ConversationViewProps {
  conversation: Conversation | null;
  isLoading: boolean;
}

export function ConversationView({ conversation, isLoading }: ConversationViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll vers le bas quand de nouveaux messages arrivent
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!conversation) {
    return null;
  }

  const messages = conversation.messages || [];

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p>Aucun message dans cette conversation</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 pb-4">
      {messages.map((message) => (
        <ChatMessage key={message.message_id} message={message} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}
