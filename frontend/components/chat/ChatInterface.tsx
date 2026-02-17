'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useSubmitQuery } from '@/lib/hooks/useQuery';
import { Loader2, Send, AlertCircle, CheckCircle2, FileText } from 'lucide-react';
import type { QueryResponse } from '@/types/documents';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  response?: QueryResponse;
  timestamp: Date;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { mutate: submitQuery, isPending } = useSubmitQuery();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isPending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    submitQuery(
      { question: input.trim(), top_k: 5 },
      {
        onSuccess: (data) => {
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: data.answer,
            response: data,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        },
        onError: (error: any) => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: error.response?.data?.detail || 'Sorry, I encountered an error. Please try again.',
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMessage]);
        },
      }
    );
  };

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.8) {
      return <Badge className="bg-green-500"><CheckCircle2 className="w-3 h-3 mr-1" />High Confidence</Badge>;
    } else if (score >= 0.5) {
      return <Badge className="bg-yellow-500"><AlertCircle className="w-3 h-3 mr-1" />Medium Confidence</Badge>;
    } else {
      return <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" />Low Confidence</Badge>;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="text-6xl">💬</div>
            <div>
              <h3 className="text-lg font-semibold">Ask me anything about company policies</h3>
              <p className="text-sm text-muted-foreground mt-2">
                I'll search through company documents to provide accurate answers
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[80%] ${message.type === 'user' ? 'order-2' : 'order-1'}`}>
              <Card className={`p-4 ${message.type === 'user' ? 'bg-primary text-primary-foreground' : ''}`}>
                <p className="whitespace-pre-wrap">{message.content}</p>

                {message.response && (
                  <div className="mt-4 space-y-3">
                    {/* Confidence Score */}
                    <div className="flex items-center gap-2">
                      {getConfidenceBadge(message.response.confidence_score)}
                      <span className="text-xs text-muted-foreground">
                        {Math.round(message.response.confidence_score * 100)}% confident
                      </span>
                    </div>

                    {/* HR Escalation Warning */}
                    {message.response.should_escalate && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5" />
                          <div className="text-sm">
                            <p className="font-medium text-yellow-900">HR Contact Recommended</p>
                            <p className="text-yellow-700 mt-1">{message.response.escalation_reason}</p>
                            {message.response.hr_contact && (
                              <p className="mt-2 text-yellow-800">
                                Contact: {message.response.hr_contact.name} ({message.response.hr_contact.email})
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Sources */}
                    {message.response.sources && message.response.sources.length > 0 && (
                      <>
                        <Separator />
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-muted-foreground">Sources:</p>
                          {message.response.sources.map((source, idx) => (
                            <div key={idx} className="text-xs bg-muted p-2 rounded">
                              <div className="flex items-center gap-2 mb-1">
                                <FileText className="w-3 h-3" />
                                <span className="font-medium">{source.title}</span>
                                {source.category && (
                                  <Badge variant="outline" className="text-xs">{source.category}</Badge>
                                )}
                              </div>
                              <p className="text-muted-foreground line-clamp-2">{source.chunk_text}</p>
                              <p className="text-muted-foreground mt-1">
                                Relevance: {Math.round(source.similarity * 100)}%
                              </p>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </Card>
              <p className="text-xs text-muted-foreground mt-1 px-2">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {isPending && (
          <div className="flex justify-start">
            <Card className="p-4">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Searching documents...</span>
              </div>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4 bg-background">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about company policies..."
            className="min-h-[60px] resize-none"
            disabled={isPending}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <Button type="submit" size="icon" disabled={isPending || !input.trim()}>
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </form>
        <p className="text-xs text-muted-foreground mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
