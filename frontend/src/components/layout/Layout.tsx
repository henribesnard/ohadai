import React from 'react';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
  selectedConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
}

export function Layout({
  children,
  selectedConversationId,
  onSelectConversation,
  onNewConversation,
}: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar
        selectedConversationId={selectedConversationId}
        onSelectConversation={onSelectConversation}
        onNewConversation={onNewConversation}
      />

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
