import { useCallback, useEffect, useRef, useState } from 'react';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '@types';
import { v4 as uuidv4 } from 'uuid';
import { Message } from '@renderer/shared/types';

interface StreamStatePayload {
  isStreaming: boolean;
  currentText: string;
  thinkingText: string;
  toolCalls: any[];
  hasError: boolean;
  errorMessage: string | null;
}

interface QueuedMessage {
  content: string;
  userMessageId: string;
}

export function useChatMessages() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);
  const streamMessageId = useRef<string | null>(null);
  const queueRef = useRef<QueuedMessage[]>([]);
  const isStreamingRef = useRef(false);
  const readyForNextRef = useRef(false);

  const setStreamingState = useCallback((value: boolean) => {
    isStreamingRef.current = value;
    setIsStreaming(value);
  }, []);

  const updateMessage = useCallback((id: string, update: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === id ? { ...message, ...update } : message))
    );
  }, []);

  const updateStreamingMessage = useCallback(
    (update: Partial<Message>) => {
      if (!streamMessageId.current) {
        return;
      }

      updateMessage(streamMessageId.current, update);
    },
    [updateMessage]
  );

  const startStreaming = useCallback(
    async (content: string, userMessageId: string) => {
      if (isStreamingRef.current) {
        queueRef.current.push({ content, userMessageId });
        setQueuedCount(queueRef.current.length);
        updateMessage(userMessageId, { status: 'queued' });
        return;
      }

      const assistantMessageId = uuidv4();
      const placeholder: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        isStreaming: true,
        toolCalls: [],
      };

      streamMessageId.current = assistantMessageId;
      updateMessage(userMessageId, { status: 'sent' });
      setMessages((prev) => [...prev, placeholder]);
      setStreamingState(true);

      try {
        const result = await ipcRenderer.invoke(IPC_CHANNELS.SEND_MESSAGE, content);
        if (!result?.success) {
          updateStreamingMessage({
            isStreaming: false,
            content: result?.error || 'Failed to send message',
          });
          streamMessageId.current = null;
          setStreamingState(false);
          readyForNextRef.current = true;
        }
      } catch (error) {
        updateStreamingMessage({
          isStreaming: false,
          content: error instanceof Error ? error.message : 'Failed to send message',
        });
        streamMessageId.current = null;
        setStreamingState(false);
        readyForNextRef.current = true;
      }
    },
    [updateMessage, updateStreamingMessage, setStreamingState]
  );

  const processQueue = useCallback(() => {
    if (isStreamingRef.current) {
      return;
    }

    const next = queueRef.current.shift();
    if (!next) {
      setQueuedCount(0);
      return;
    }

    setQueuedCount(queueRef.current.length);
    void startStreaming(next.content, next.userMessageId);
  }, [startStreaming]);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: Date.now(),
        toolCalls: [],
        status: isStreamingRef.current ? 'queued' : 'sent',
      };

      setMessages((prev) => [...prev, userMessage]);

      if (isStreamingRef.current) {
        queueRef.current.push({ content, userMessageId: userMessage.id });
        setQueuedCount(queueRef.current.length);
        return;
      }

      await startStreaming(content, userMessage.id);
    },
    [startStreaming]
  );

  const interrupt = useCallback(async () => {
    await ipcRenderer.invoke(IPC_CHANNELS.INTERRUPT_RESPONSE);
  }, []);

  useEffect(() => {
    const handleStream = (_event: unknown, payload: any) => {
      if (!payload) {
        return;
      }

      if (payload.type === 'stateChange' && payload.state) {
        const state = payload.state as StreamStatePayload;
        updateStreamingMessage({
          content: state.currentText,
          thinkingContent: state.thinkingText || undefined,
          toolCalls: state.toolCalls || [],
          isStreaming: state.isStreaming,
        });
        setStreamingState(state.isStreaming);

        if (!state.isStreaming && readyForNextRef.current) {
          readyForNextRef.current = false;
          processQueue();
        }
      }

      if (payload.type === 'interrupted' && payload.message) {
        updateStreamingMessage({
          content: payload.message.content,
          thinkingContent: payload.message.thinkingContent,
          toolCalls: payload.message.toolCalls || [],
          isStreaming: false,
        });
        streamMessageId.current = null;
        setStreamingState(false);
        processQueue();
      }
    };

    const handleResponse = (_event: unknown, message: Message) => {
      if (streamMessageId.current) {
        updateStreamingMessage({
          content: message.content,
          thinkingContent: message.thinkingContent,
          toolCalls: message.toolCalls || [],
          isStreaming: false,
        });
      } else {
        setMessages((prev) => [...prev, message]);
      }
      streamMessageId.current = null;
      readyForNextRef.current = true;
      setStreamingState(false);
    };

  const handleError = (_event: unknown, errorMessage: string) => {
      setMessages((prev) =>
        prev.map((message) => {
          if (message.id !== streamMessageId.current) {
            return message;
          }
          const existing = (message.content || '').trim();
          const nextContent = existing || errorMessage;
          return {
            ...message,
            isStreaming: false,
            content: nextContent,
          };
        })
      );
      streamMessageId.current = null;
      readyForNextRef.current = true;
      setStreamingState(false);
    };

    ipcRenderer.on(IPC_CHANNELS.CLAUDE_STREAM, handleStream);
    ipcRenderer.on(IPC_CHANNELS.CLAUDE_RESPONSE, handleResponse);
    ipcRenderer.on(IPC_CHANNELS.CLAUDE_ERROR, handleError);

    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.CLAUDE_STREAM, handleStream);
      ipcRenderer.removeListener(IPC_CHANNELS.CLAUDE_RESPONSE, handleResponse);
      ipcRenderer.removeListener(IPC_CHANNELS.CLAUDE_ERROR, handleError);
    };
  }, [processQueue, setStreamingState, updateStreamingMessage]);

  return {
    messages,
    isStreaming,
    queuedCount,
    sendMessage,
    interrupt,
  };
}
