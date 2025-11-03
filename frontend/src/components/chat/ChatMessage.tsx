/**
 * Composant pour afficher un message de chat
 */
import React from 'react';
import type { Message } from '@/features/conversations/types';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Card } from '@/components/ui/card';
import { User, Bot } from 'lucide-react';
import { SearchResults } from '@/components/search/SearchResults';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.is_user;
  const sources = message.metadata?.sources || [];

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} animate-fadeIn`}>
      {/* Avatar */}
      <Avatar className="shrink-0">
        <AvatarFallback className={isUser ? 'bg-muted' : 'bg-primary text-primary-foreground'}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      {/* Contenu du message */}
      <div className={`flex flex-col gap-2 max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bulle de message */}
        <Card
          className={`p-4 ${
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-card text-card-foreground border-border'
          }`}
        >
          <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>

          {/* Afficher les performances si disponibles */}
          {!isUser && message.metadata?.performance && (
            <div className="mt-3 pt-3 border-t border-border/30 text-xs opacity-70">
              <div className="flex gap-3">
                {message.metadata.performance.total_time && (
                  <span>⏱️ {message.metadata.performance.total_time.toFixed(2)}s</span>
                )}
              </div>
            </div>
          )}
        </Card>

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground px-1">
          {new Date(message.created_at).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>

        {/* Sources - uniquement pour les messages de l'IA */}
        {!isUser && sources.length > 0 && (
          <div className="w-full mt-2">
            <SearchResults sources={sources} isLoading={false} />
          </div>
        )}
      </div>
    </div>
  );
}
