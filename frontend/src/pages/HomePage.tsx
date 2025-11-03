import React, { useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { ConversationView } from '@/components/chat/ConversationView';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Send } from 'lucide-react';
import { useConversation } from '@/features/conversations/hooks/useConversations';
import { conversationsService } from '@/features/conversations/services/conversationsService';

const exampleQuestions = [
  'Comment comptabiliser les immobilisations corporelles?',
  'Quelles sont les règles d\'amortissement selon SYSCOHADA?',
  'Comment établir un bilan conforme OHADA?',
  'Qu\'est-ce que le plan comptable SYSCOHADA révisé?',
];

export function HomePage() {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Charger la conversation sélectionnée
  const { conversation, isLoading: isLoadingConversation, refetch } = useConversation(selectedConversationId);

  // Gérer la sélection d'une conversation
  const handleSelectConversation = (conversationId: string) => {
    setSelectedConversationId(conversationId);
  };

  // Gérer la création d'une nouvelle conversation
  const handleNewConversation = () => {
    setSelectedConversationId(null);
    setInputMessage('');
  };

  // Gérer l'envoi d'un message
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    setIsSending(true);
    try {
      if (selectedConversationId) {
        // Envoyer le message dans la conversation existante
        await conversationsService.sendMessage(selectedConversationId, inputMessage);
        refetch();
      } else {
        // Créer une nouvelle conversation avec ce message
        const result = await conversationsService.createMessage({
          content: inputMessage,
          conversation_title: inputMessage.substring(0, 50) + (inputMessage.length > 50 ? '...' : ''),
        });
        setSelectedConversationId(result.conversation_id);
      }
      setInputMessage('');
    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error);
      alert('Erreur lors de l\'envoi du message');
    } finally {
      setIsSending(false);
    }
  };

  // Gérer le clic sur une question d'exemple
  const handleExampleClick = async (question: string) => {
    setInputMessage(question);
    // Auto-envoyer la question
    setIsSending(true);
    try {
      const result = await conversationsService.createMessage({
        content: question,
        conversation_title: question.substring(0, 50) + (question.length > 50 ? '...' : ''),
      });
      setSelectedConversationId(result.conversation_id);
      setInputMessage('');
    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error);
      alert('Erreur lors de l\'envoi du message');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Layout
      selectedConversationId={selectedConversationId}
      onSelectConversation={handleSelectConversation}
      onNewConversation={handleNewConversation}
    >
      <div className="h-full flex flex-col">
        {/* Zone de messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedConversationId ? (
            // Afficher la conversation
            <div className="max-w-4xl mx-auto">
              <ConversationView
                conversation={conversation || null}
                isLoading={isLoadingConversation}
              />
            </div>
          ) : (
            // Afficher l'écran d'accueil avec les exemples de questions
            <div className="max-w-4xl mx-auto space-y-8">
              <div className="text-center space-y-4 py-12">
                <h1 className="text-4xl font-bold text-foreground">
                  Bienvenue sur OHAD'AI
                </h1>
                <p className="text-xl text-muted-foreground">
                  Expert en comptabilité OHADA et SYSCOHADA
                </p>
              </div>

              {/* Questions d'exemple */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {exampleQuestions.map((question, index) => (
                  <Card
                    key={index}
                    className="p-4 hover:bg-accent transition-colors cursor-pointer"
                    onClick={() => handleExampleClick(question)}
                  >
                    <p className="text-sm text-foreground">{question}</p>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Zone de saisie du message */}
        <div className="border-t border-border bg-background p-4">
          <div className="max-w-4xl mx-auto">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="relative"
            >
              <Input
                type="text"
                placeholder="Posez votre question sur le plan comptable OHADA..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                className="pr-16 py-6 text-base"
                disabled={isSending}
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2">
                <Button
                  type="submit"
                  size="icon"
                  disabled={!inputMessage.trim() || isSending}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Layout>
  );
}
