'use client';

import { useState, useRef, useEffect } from 'react';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardHeader } from '@/components/layout/DashboardHeader';
import { ChatMessage } from '@/components/qa/ChatMessage';
import { ChatInput } from '@/components/qa/ChatInput';
import { Button } from '@/components/ui/button';
import { useSubmitQuery, useQueryHistory } from '@/lib/hooks/useQuery';
import { Sparkles, Loader2, Plus, ArrowRight } from 'lucide-react';
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
      <div className="flex flex-col h-screen bg-background relative overflow-hidden">
        {/* Decorative background blobs for QA */}
        <div className="absolute top-[20%] right-[-5%] w-[30%] h-[30%] rounded-full bg-primary/10 blur-[100px] pointer-events-none" />
        <div className="absolute bottom-[10%] left-[-5%] w-[25%] h-[25%] rounded-full bg-purple-500/10 blur-[100px] pointer-events-none" />

        <div className="z-10 relative"><DashboardHeader /></div>

        <div className="z-10 flex-1 overflow-hidden flex flex-col max-w-5xl mx-auto w-full px-4">
          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col glass-panel my-4 rounded-3xl overflow-hidden shadow-2xl border-white/20 dark:border-white/10">
            <div className="p-4 sm:p-6 border-b border-border/50 bg-background/50 backdrop-blur-sm flex items-center justify-between z-20">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                  Policy Assistant
                </h2>
                <p className="text-sm sm:text-base text-muted-foreground mt-1">
                  Ask anything about your company's documents
                </p>
              </div>
              <Button
                variant="outline"
                onClick={handleNewConversation}
                disabled={messages.length === 0}
                className="rounded-full px-4 sm:px-6 shadow-sm hover:shadow transition-all"
              >
                <Plus className="w-4 h-4 sm:mr-2" />
                <span className="hidden sm:inline">New Chat</span>
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 sm:p-6 scroll-smooth z-10 relative">
              <div className="max-w-3xl mx-auto h-full">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full animate-fade-in-up">
                    <div className="glass-panel p-8 sm:p-12 rounded-3xl max-w-2xl text-center shadow-[0_0_40px_rgba(37,99,235,0.1)] relative overflow-hidden border-primary/20">
                      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500" />
                      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 text-primary mb-6 shadow-inner ring-1 ring-primary/20 animate-pulse-glow">
                        <Sparkles className="w-8 h-8" />
                      </div>
                      <h3 className="text-2xl sm:text-3xl font-bold mb-4 tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                        How can I help you today?
                      </h3>
                      <p className="text-muted-foreground mb-8 text-base sm:text-lg leading-relaxed">
                        I'm your AI assistant trained on your company's knowledge base. Here are some examples of what you can ask me:
                      </p>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                        {[
                          "What is the vacation policy?",
                          "How do I request time off?",
                          "What are remote work guidelines?",
                          "Explain expense reimbursements."
                        ].map((example, i) => (
                           <button
                             key={i}
                             onClick={() => handleSubmit(example)}
                             className="flex items-center justify-between p-4 rounded-xl border border-border/50 bg-background/50 hover:bg-muted/50 transition-all hover:-translate-y-0.5 hover:shadow-sm group text-sm sm:text-base text-muted-foreground hover:text-foreground"
                           >
                             <span className="truncate pr-2">{example}</span>
                             <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity text-primary shrink-0" />
                           </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {messages.map((message, idx) => (
                      <ChatMessage key={idx} message={message} />
                    ))}
                    <div ref={messagesEndRef} className="h-4" />
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 sm:p-6 border-t border-border/50 bg-background/80 backdrop-blur-xl z-20">
              <div className="max-w-3xl mx-auto">
                <ChatInput
                  onSubmit={handleSubmit}
                  isLoading={isPending}
                  disabled={isPending}
                />
                <div className="text-center mt-3 text-xs text-muted-foreground font-medium">
                  AI can make mistakes. Verify important policy information with HR.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

