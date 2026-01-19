import React from 'react';
import { Message } from '@renderer/shared/types';
import { Message as MessageComponent } from './Message';
import { motion, AnimatePresence } from 'framer-motion';
import { useStickToBottom } from '@renderer/shared/hooks/useStickToBottom';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const containerRef = useStickToBottom<HTMLDivElement>([messages.length]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.length === 0 && (
        <div className="text-sm text-neutral-500 text-center py-6">
          Start a conversation to see messages here.
        </div>
      )}
      <AnimatePresence>
        {messages.map((message, index) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.3,
              delay: index * 0.04,
              ease: 'easeOut',
            }}
          >
            <MessageComponent message={message} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
