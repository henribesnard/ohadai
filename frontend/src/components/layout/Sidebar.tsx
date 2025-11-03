import React from 'react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { MessageSquarePlus, Settings, LogOut, LayoutDashboard } from 'lucide-react';
import { useAuth } from '@/features/auth/context/AuthContext';
import { useConversations } from '@/features/conversations/hooks/useConversations';

interface SidebarProps {
  selectedConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
}

// Fonction utilitaire pour formater les dates
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'il y a quelques instants';
  if (diffInSeconds < 3600) return `il y a ${Math.floor(diffInSeconds / 60)} minutes`;
  if (diffInSeconds < 86400) return `il y a ${Math.floor(diffInSeconds / 3600)} heures`;
  if (diffInSeconds < 604800) return `il y a ${Math.floor(diffInSeconds / 86400)} jours`;
  return date.toLocaleDateString('fr-FR');
}

export function Sidebar({
  selectedConversationId,
  onSelectConversation,
  onNewConversation,
}: SidebarProps) {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const { user, logout } = useAuth();
  const { conversations, isLoadingConversations } = useConversations();

  return (
    <aside className="w-64 h-screen bg-background border-r border-border flex flex-col">
      {/* Header avec logo/titre */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-lg">O</span>
          </div>
          <span className="font-semibold text-lg">OHAD'AI</span>
        </div>
      </div>

      {/* Bouton Nouvelle conversation */}
      <div className="p-4">
        <Button
          className="w-full"
          variant="default"
          onClick={onNewConversation}
        >
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          Nouvelle conversation
        </Button>
      </div>

      {/* Liste des conversations (scrollable) */}
      <div className="flex-1 overflow-y-auto px-2">
        {isLoadingConversations ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            Chargement...
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            Aucune conversation
          </div>
        ) : (
          <div className="space-y-1">
            {conversations.map((conversation) => {
              const messageCount = conversation.messages?.length || 0;
              const isSelected = conversation.conversation_id === selectedConversationId;

              return (
                <button
                  key={conversation.conversation_id}
                  onClick={() => onSelectConversation(conversation.conversation_id)}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors group ${
                    isSelected ? 'bg-accent' : 'hover:bg-accent'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate text-foreground">
                        {conversation.title}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                        <span>{formatRelativeTime(conversation.updated_at)}</span>
                        {messageCount > 0 && (
                          <>
                            <span>•</span>
                            <span>{messageCount} message{messageCount > 1 ? 's' : ''}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* User menu en bas */}
      <div className="border-t border-border">
        <div className="relative">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="w-full p-4 flex items-center gap-3 hover:bg-accent transition-colors"
          >
            <Avatar>
              <AvatarFallback className="bg-primary text-primary-foreground">
                {user?.name ? user.name.substring(0, 2).toUpperCase() : user?.email?.substring(0, 2).toUpperCase() || 'U'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 text-left">
              <div className="text-sm font-medium">{user?.name || 'Utilisateur'}</div>
              <div className="text-xs text-muted-foreground truncate">{user?.email || ''}</div>
            </div>
            <svg
              className={`w-4 h-4 transition-transform ${isMenuOpen ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Dropdown menu */}
          {isMenuOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-2 mx-2 bg-popover border border-border rounded-md shadow-lg overflow-hidden animate-fadeIn">
              <button className="w-full px-4 py-2 text-sm text-left hover:bg-accent flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4" />
                Tableau de bord
              </button>
              <button className="w-full px-4 py-2 text-sm text-left hover:bg-accent flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Configuration
              </button>
              <div className="border-t border-border"></div>
              <button
                onClick={logout}
                className="w-full px-4 py-2 text-sm text-left hover:bg-accent flex items-center gap-2 text-destructive"
              >
                <LogOut className="h-4 w-4" />
                Se déconnecter
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
