/**
 * Types pour les conversations
 */

export interface Message {
  message_id: string;
  conversation_id: string;
  user_id: string;
  content: string;
  is_user: boolean;
  created_at: string;
  metadata?: {
    performance?: {
      total_time?: number;
      embedding_time?: number;
      search_time?: number;
      generation_time?: number;
    };
    sources?: Source[];
  };
}

export interface Source {
  document_id: string;
  title: string;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

export interface Conversation {
  conversation_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface ConversationCreate {
  title: string;
}

export interface ConversationUpdate {
  title: string;
}

export interface MessageCreate {
  content: string;
  conversation_id?: string;
  conversation_title?: string;
}

export interface MessageResponse {
  conversation_id: string;
  messages: Message[];
  user_message_id: string;
  ia_message_id: string;
}
