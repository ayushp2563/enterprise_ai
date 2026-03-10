'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, ChevronDown, ChevronUp, Bot, User } from 'lucide-react';
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
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in-up`} style={{ animationDuration: '0.4s' }}>
      <div className={`flex gap-3 max-w-[85%] sm:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center shadow-sm ${
          isUser 
            ? 'bg-gradient-to-br from-primary to-indigo-600 text-white' 
            : 'bg-white dark:bg-gray-800 border border-border text-primary'
        }`}>
          {isUser ? <User className="w-4 h-4 sm:w-5 sm:h-5" /> : <Bot className="w-4 h-4 sm:w-5 sm:h-5" />}
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className={`relative px-5 py-3.5 rounded-2xl sm:rounded-3xl shadow-sm text-sm sm:text-base leading-relaxed ${
            isUser
              ? 'bg-gradient-to-br from-primary to-indigo-600 text-primary-foreground rounded-tr-sm'
              : 'bg-white dark:bg-muted border border-border/50 text-foreground rounded-tl-sm'
          }`}>
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
            
            {/* Sources section for Assistant */}
            {!isUser && message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-4 border-t border-border/50 w-full min-w-[200px]">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSources(!showSources)}
                  className="w-full justify-between h-8 px-2 hover:bg-muted/50 text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span className="flex items-center gap-2 font-medium">
                    <FileText className="w-3.5 h-3.5 text-primary/70" />
                    {message.sources.length} Source{message.sources.length > 1 ? 's' : ''}
                  </span>
                  {showSources ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </Button>
                
                {showSources && (
                  <div className="mt-3 space-y-3 animate-fade-in-up" style={{ animationDuration: '0.3s' }}>
                    {message.sources.map((source, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 bg-background/50 border border-border/50 rounded-xl text-sm transition-all hover:bg-background hover:shadow-sm"
                      >
                        <div className="flex items-start sm:items-center justify-between gap-2 mb-2 flex-col sm:flex-row">
                          <span className="font-semibold text-foreground/90 leading-tight">
                            {source.title}
                          </span>
                          <Badge variant="secondary" className="text-[10px] sm:text-xs font-medium bg-primary/10 text-primary border-0">
                            {(source.similarity * 100).toFixed(0)}% match
                          </Badge>
                        </div>
                        <p className="text-muted-foreground text-xs sm:text-sm line-clamp-3 leading-relaxed">
                          {source.chunk_text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Timestamp */}
          {message.timestamp && (
            <p className={`text-[10px] sm:text-xs text-muted-foreground/70 mt-1.5 px-2 font-medium ${isUser ? 'text-right' : 'text-left'}`}>
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
