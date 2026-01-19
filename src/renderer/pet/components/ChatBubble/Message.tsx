import React from 'react';
import { Message } from '@renderer/shared/types';
import { StreamingMessage } from './StreamingMessage';
import { ThinkingBlock } from './ThinkingBlock';
import { ToolCallDisplay } from './ToolCallDisplay';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles, User } from 'lucide-react';

interface MessageProps {
  message: Message;
}

export function Message({ message }: MessageProps) {
  const isStreaming = message.isStreaming;
  const isUser = message.role === 'user';
  const isQueued = isUser && message.status === 'queued';

  return (
    <div className={`flex gap-3 p-4 rounded-lg border ${
      isUser ? 'bg-neutral-0 border-primary-200' : 'bg-neutral-50 border-neutral-200'
    } ${isStreaming ? 'animate-pulse-subtle' : ''} ${isQueued ? 'border-dashed opacity-80' : ''}`}>
      <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-primary-500 text-white' : 'bg-secondary-500 text-white'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      <div className="flex-1 min-w-0">
        {isQueued && (
          <div className="text-[10px] uppercase tracking-wide text-neutral-400 mb-1">
            Queued
          </div>
        )}
        {isStreaming ? (
          <StreamingMessage content={message.content} thinkingContent={message.thinkingContent} />
        ) : (
          <div className="prose prose-sm max-w-none text-neutral-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}

        {message.thinkingContent && !isStreaming && (
          <ThinkingBlock content={message.thinkingContent} />
        )}

        {message.toolCalls && (
          <ToolCallDisplay toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
}
