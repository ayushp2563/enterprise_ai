'use client';

import { useState, useRef, useEffect } from 'react';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardHeader } from '@/components/layout/DashboardHeader';
import { ChatMessage } from '@/components/qa/ChatMessage';
import { ChatInput } from '@/components/qa/ChatInput';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useSubmitQuery, useQueryHistory } from '@/lib/hooks/useQuery';
import { MessageSquare, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';
import type { QueryResponse } from '@/types/documents';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: QueryResponse['sources'];
  timestamp: string;
}

export default function QAPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { mutate: submitQuery, isPending } = useSubmitQuery();
  const { data: history, isLoading: isLoadingHistory } = useQueryHistory();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (question: string) => {
    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Submit query
    submitQuery(
      { question, conversation_id: conversationId },
      {
        onSuccess: (data) => {
          // Add assistant response
          const assistantMessage: Message = {
            role: 'assistant',
            content: data.answer,
            sources: data.sources,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
          
          // Update conversation ID
          if (data.conversation_id) {
            setConversationId(data.conversation_id);
          }
        },
        onError: (error: any) => {
          toast.error(error.response?.data?.detail || 'Failed to get answer');
          // Remove the user message on error
          setMessages((prev) => prev.slice(0, -1));
        },
      }
    );
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    toast.success('Started new conversation');
  };

  return (
    <ProtectedRoute allowedRoles={['company_admin', 'hr_manager', 'employee']}>
      <div className="flex flex-col h-screen">
        <DashboardHeader />
        
        <div className="flex-1 overflow-hidden flex">
          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col">
            <div className="p-6 border-b">
              <div className="max-w-4xl mx-auto flex items-center justify-between">
                <div>
                  <h2 className="text-3xl font-bold tracking-tight">Ask Questions</h2>
                  <p className="text-muted-foreground">
                    Get instant answers from your company's policy documents
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={handleNewConversation}
                  disabled={messages.length === 0}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  New Chat
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-6">
              <div className="max-w-4xl mx-auto">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <Card className="max-w-2xl">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <MessageSquare className="w-6 h-6" />
                          Welcome to Q&A
                        </CardTitle>
                        <CardDescription>
                          Ask questions about your company's policies, procedures, and documents.
                          Our AI assistant will search through all uploaded documents to provide accurate answers.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 text-sm text-muted-foreground">
                          <p><strong>Example questions:</strong></p>
                          <ul className="list-disc list-inside space-y-1">
                            <li>What is the vacation policy?</li>
                            <li>How do I request time off?</li>
                            <li>What are the remote work guidelines?</li>
                            <li>What is the expense reimbursement process?</li>
                          </ul>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  <>
                    {messages.map((message, idx) => (
                      <ChatMessage key={idx} message={message} />
                    ))}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>
            </div>

            <div className="p-6 border-t bg-background">
              <div className="max-w-4xl mx-auto">
                <ChatInput
                  onSubmit={handleSubmit}
                  isLoading={isPending}
                  disabled={isPending}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
