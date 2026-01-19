export interface ToolCallInfo {
  id: string;
  name: string;
  input: Record<string, unknown>;
  result?: string;
  isExpanded?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  thinkingContent?: string;
  toolCalls?: ToolCallInfo[];
  status?: 'queued' | 'sent';
}

export interface FileReference {
  id: string;
  path: string;
  name: string;
  content?: string;
}

export interface Session {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
}

export interface PetState {
  x: number;
  y: number;
  isVisible: boolean;
  isAnimating: boolean;
  scale: number;
  rotation: number;
}

export interface ChatState {
  isOpen: boolean;
  messages: Message[];
  inputValue: string;
  isTyping: boolean;
  isStreaming: boolean;
}

export interface Settings {
  theme: 'light' | 'dark' | 'auto';
  language: 'zh-CN' | 'en-US';
  autoStart: boolean;
  startupBehavior: 'minimized' | 'visible' | 'hidden';
  animations: boolean;
  sounds: boolean;
}

export interface Tool {
  name: string;
  description: string;
  parameters?: ToolParameter[];
}

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  required?: boolean;
  default?: any;
}

export interface ToolUseRequest {
  tool: string;
  parameters: Record<string, any>;
  requestId: string;
}

export interface ToolUseResponse {
  requestId: string;
  result: any;
  error?: string;
}
