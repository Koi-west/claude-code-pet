import { SDKUserMessage, MessageContent } from '../../types';

/**
 * MessageChannel provides a queue-based interface for sending messages
 * to the Claude Code persistent query. This enables low-latency follow-up
 * messages without cold-start delays.
 */
export class MessageChannel implements AsyncIterable<SDKUserMessage> {
  private queue: SDKUserMessage[] = [];
  private resolveNext: ((value: SDKUserMessage | null) => void) | null = null;
  private closed = false;
  private sessionId: string = '';

  /**
   * Set the session ID for messages
   */
  setSessionId(id: string): void {
    this.sessionId = id;
  }

  /**
   * Get the current session ID
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Enqueue a message to be sent to Claude Code
   */
  enqueue(message: SDKUserMessage): void {
    if (this.closed) {
      throw new Error('MessageChannel is closed');
    }

    // Update session ID if not set in message
    if (!message.session_id && this.sessionId) {
      message.session_id = this.sessionId;
    }

    if (this.resolveNext) {
      this.resolveNext(message);
      this.resolveNext = null;
    } else {
      this.queue.push(message);
    }
  }

  /**
   * Create a user message from text content
   */
  createTextMessage(content: string): SDKUserMessage {
    return {
      type: 'user',
      message: {
        role: 'user',
        content,
      },
      parent_tool_use_id: null,
      session_id: this.sessionId,
    };
  }

  /**
   * Create a user message with mixed content (text + images)
   */
  createMixedMessage(text: string, images: Array<{ data: string; mediaType: string }>): SDKUserMessage {
    const content: MessageContent[] = [];

    // Add images first
    for (const image of images) {
      content.push({
        type: 'image',
        source: {
          type: 'base64',
          media_type: image.mediaType,
          data: image.data,
        },
      });
    }

    // Add text
    if (text.trim()) {
      content.push({
        type: 'text',
        text,
      });
    }

    return {
      type: 'user',
      message: {
        role: 'user',
        content,
      },
      parent_tool_use_id: null,
      session_id: this.sessionId,
    };
  }

  /**
   * Send a text message
   */
  sendText(content: string): void {
    this.enqueue(this.createTextMessage(content));
  }

  /**
   * Close the message channel
   */
  close(): void {
    this.closed = true;
    if (this.resolveNext) {
      this.resolveNext(null);
      this.resolveNext = null;
    }
  }

  /**
   * Check if the channel is closed
   */
  isClosed(): boolean {
    return this.closed;
  }

  /**
   * Reopen a closed channel
   */
  reopen(): void {
    this.closed = false;
  }

  /**
   * Clear the message queue
   */
  clear(): void {
    this.queue = [];
  }

  /**
   * Get the number of pending messages
   */
  get pendingCount(): number {
    return this.queue.length;
  }

  /**
   * Async iterator implementation for consuming messages
   */
  async *[Symbol.asyncIterator](): AsyncIterator<SDKUserMessage> {
    while (!this.closed) {
      if (this.queue.length > 0) {
        yield this.queue.shift()!;
      } else {
        const message = await new Promise<SDKUserMessage | null>((resolve) => {
          this.resolveNext = resolve;
        });

        if (message === null) {
          break;
        }

        yield message;
      }
    }
  }
}

export default MessageChannel;
