'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { QueryResponse } from '@/types/documents';

interface ChatMessageProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
    sources?: QueryResponse['sources'];
    timestamp?: string;
  };
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        <Card className={isUser ? 'bg-primary text-primary-foreground' : ''}>
          <CardContent className="p-4">
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
            
            {!isUser && message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSources(!showSources)}
                  className="w-full justify-between"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    {message.sources.length} Source{message.sources.length > 1 ? 's' : ''}
                  </span>
                  {showSources ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </Button>
                
                {showSources && (
                  <div className="mt-2 space-y-2">
                    {message.sources.map((source, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-muted rounded-lg text-sm"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{source.document_title}</span>
                          <Badge variant="outline" className="text-xs">
                            {(source.relevance_score * 100).toFixed(0)}% match
                          </Badge>
                        </div>
                        <p className="text-muted-foreground line-clamp-3">
                          {source.chunk_text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        
        {message.timestamp && (
          <p className="text-xs text-muted-foreground mt-1 px-2">
            {new Date(message.timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
