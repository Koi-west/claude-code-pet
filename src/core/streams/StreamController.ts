import { EventEmitter } from 'events';
import { StreamEvent, ChatMessage, ToolCallInfo } from '../../types';
import { v4 as uuidv4 } from 'uuid';

export interface StreamState {
  isStreaming: boolean;
  currentText: string;
  thinkingText: string;
  toolCalls: ToolCallInfo[];
  hasError: boolean;
  errorMessage: string | null;
}

/**
 * StreamController processes streaming responses from Claude Code
 * and provides a typewriter effect for displaying text.
 */
export class StreamController extends EventEmitter {
  private state: StreamState = {
    isStreaming: false,
    currentText: '',
    thinkingText: '',
    toolCalls: [],
    hasError: false,
    errorMessage: null,
  };

  // Typewriter effect configuration
  private typewriterSpeed = 20; // ms per character
  private typewriterBuffer: string[] = [];
  private typewriterInterval: ReturnType<typeof setInterval> | null = null;
  private pendingText = '';

  constructor(options?: { typewriterSpeed?: number }) {
    super();
    if (options?.typewriterSpeed) {
      this.typewriterSpeed = options.typewriterSpeed;
    }
  }

  /**
   * Get the current stream state
   */
  getState(): StreamState {
    return { ...this.state };
  }

  /**
   * Start streaming
   */
  startStream(): void {
    this.state = {
      isStreaming: true,
      currentText: '',
      thinkingText: '',
      toolCalls: [],
      hasError: false,
      errorMessage: null,
    };
    this.pendingText = '';
    this.startTypewriter();
    this.emit('streamStart');
  }

  /**
   * Process a stream event
   */
  processEvent(event: StreamEvent): void {
    switch (event.type) {
      case 'text':
        this.handleTextEvent(event.content);
        break;

      case 'thinking':
        this.handleThinkingEvent(event.content);
        break;

      case 'tool_use':
        this.handleToolUseEvent(event);
        break;

      case 'tool_result':
        this.handleToolResultEvent(event);
        break;

      case 'done':
        this.handleDoneEvent();
        break;

      case 'error':
        this.handleErrorEvent(event.content);
        break;

      case 'session_id':
        this.emit('sessionId', event.id);
        break;
    }
  }

  /**
   * Handle text content
   */
  private handleTextEvent(content: string): void {
    this.pendingText += content;

    // Add to typewriter buffer character by character
    for (const char of content) {
      this.typewriterBuffer.push(char);
    }

    this.emit('textChunk', content);
  }

  /**
   * Handle thinking content
   */
  private handleThinkingEvent(content: string): void {
    this.state.thinkingText += content;
    this.emit('thinkingChunk', content);
    this.emit('stateChange', this.getState());
  }

  /**
   * Handle tool use start
   */
  private handleToolUseEvent(event: { id: string; name: string; input: Record<string, unknown> }): void {
    const toolCall: ToolCallInfo = {
      id: event.id,
      name: event.name,
      input: event.input,
      isExpanded: false,
    };

    this.state.toolCalls.push(toolCall);
    this.emit('toolUse', toolCall);
    this.emit('stateChange', this.getState());
  }

  /**
   * Handle tool result
   */
  private handleToolResultEvent(event: { id: string; content: string }): void {
    const toolCall = this.state.toolCalls.find((tc) => tc.id === event.id);
    if (toolCall) {
      toolCall.result = event.content;
      this.emit('toolResult', { id: event.id, content: event.content });
      this.emit('stateChange', this.getState());
    }
  }

  /**
   * Handle stream completion
   */
  private handleDoneEvent(): void {
    // Flush remaining text immediately
    this.flushTypewriter();
    this.stopTypewriter();

    this.state.isStreaming = false;
    this.state.currentText = this.pendingText;

    this.emit('streamEnd', this.createMessage());
    this.emit('stateChange', this.getState());
  }

  /**
   * Handle error
   */
  private handleErrorEvent(content: string): void {
    this.flushTypewriter();
    this.state.currentText = this.pendingText;
    this.stopTypewriter();

    this.state.isStreaming = false;
    this.state.hasError = true;
    this.state.errorMessage = content;

    this.emit('error', content);
    this.emit('stateChange', this.getState());
  }

  /**
   * Start the typewriter effect
   */
  private startTypewriter(): void {
    if (this.typewriterInterval) {
      return;
    }

    this.typewriterInterval = setInterval(() => {
      if (this.typewriterBuffer.length > 0) {
        const char = this.typewriterBuffer.shift()!;
        this.state.currentText += char;
        this.emit('typewriterChar', char);
        this.emit('stateChange', this.getState());
      }
    }, this.typewriterSpeed);
  }

  /**
   * Stop the typewriter effect
   */
  private stopTypewriter(): void {
    if (this.typewriterInterval) {
      clearInterval(this.typewriterInterval);
      this.typewriterInterval = null;
    }
  }

  /**
   * Flush remaining typewriter buffer immediately
   */
  private flushTypewriter(): void {
    while (this.typewriterBuffer.length > 0) {
      const char = this.typewriterBuffer.shift()!;
      this.state.currentText += char;
    }
  }

  /**
   * Create a ChatMessage from the current state
   */
  createMessage(): ChatMessage {
    return {
      id: uuidv4(),
      role: 'assistant',
      content: this.state.currentText,
      timestamp: Date.now(),
      thinkingContent: this.state.thinkingText || undefined,
      toolCalls: this.state.toolCalls.length > 0 ? [...this.state.toolCalls] : undefined,
    };
  }

  /**
   * Interrupt the stream
   */
  interrupt(): void {
    this.flushTypewriter();
    this.stopTypewriter();
    this.state.isStreaming = false;
    this.state.currentText = this.pendingText;
    this.emit('interrupted', this.createMessage());
    this.emit('stateChange', this.getState());
  }

  /**
   * Reset the controller state
   */
  reset(): void {
    this.stopTypewriter();
    this.typewriterBuffer = [];
    this.pendingText = '';
    this.state = {
      isStreaming: false,
      currentText: '',
      thinkingText: '',
      toolCalls: [],
      hasError: false,
      errorMessage: null,
    };
    this.emit('stateChange', this.getState());
  }

  /**
   * Set typewriter speed
   */
  setTypewriterSpeed(speed: number): void {
    this.typewriterSpeed = speed;
    if (this.typewriterInterval) {
      this.stopTypewriter();
      this.startTypewriter();
    }
  }

  /**
   * Toggle tool call expansion
   */
  toggleToolCallExpansion(toolId: string): void {
    const toolCall = this.state.toolCalls.find((tc) => tc.id === toolId);
    if (toolCall) {
      toolCall.isExpanded = !toolCall.isExpanded;
      this.emit('stateChange', this.getState());
    }
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    this.stopTypewriter();
    this.removeAllListeners();
  }
}

export default StreamController;
