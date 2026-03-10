'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, ArrowUp } from 'lucide-react';

interface ChatInputProps {
  onSubmit: (question: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSubmit, isLoading, disabled }: ChatInputProps) {
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !isLoading) {
      onSubmit(question.trim());
      setQuestion('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative group/form">
      <div className="relative flex items-end gap-2 bg-background/50 backdrop-blur-md border border-border/50 rounded-2xl shadow-sm transition-all duration-300 focus-within:shadow-[0_0_15px_rgba(37,99,235,0.15)] focus-within:border-primary/50 overflow-hidden group-focus-within/form:ring-1 group-focus-within/form:ring-primary/20">
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your company's policies..."
          disabled={disabled || isLoading}
          className="min-h-[60px] max-h-[200px] resize-none border-0 focus-visible:ring-0 bg-transparent py-4 px-5 text-base shadow-none leading-relaxed"
          autoFocus
        />
        <div className="absolute right-2 bottom-2">
          <Button
            type="submit"
            disabled={!question.trim() || isLoading || disabled}
            size="icon"
            className="h-10 w-10 sm:h-12 sm:w-12 shrink-0 rounded-xl transition-all duration-300 shadow-sm disabled:opacity-50"
            style={question.trim() && !isLoading && !disabled ? {
              background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary)/0.8))'
            } : {}}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <ArrowUp className="w-5 h-5" />
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}
