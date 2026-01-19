// Type definitions for Desktop Pet with Claude Code Integration

export type ChatState = 'idle' | 'input' | 'responding' | 'with-response';
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface Position {
  x: number;
  y: number;
}

// Message types for chat
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  thinkingContent?: string;
  toolCalls?: ToolCallInfo[];
}

export interface ToolCallInfo {
  id: string;
  name: string;
  input: Record<string, unknown>;
  result?: string;
  isExpanded?: boolean;
}

// Session types
export interface Session {
  id: string;
  name: string;
  createdAt: number;
  lastAccessedAt: number;
  messages: ChatMessage[];
  claudeSessionId?: string | null; // Claude Code SDK session ID (separate from local storage ID)
}

export interface SessionInfo {
  id: string;
  name: string;
  createdAt: number;
  lastAccessedAt: number;
  messageCount: number;
}

export interface GuiAgentConfig {
  sidecarUrl: string;
  vlmProvider: 'ollama' | 'static_openai';
  vlmBaseUrl: string;
  vlmModel: string;
  vlmApiKey?: string;
  autoStartSidecar: boolean;
  sidecarPort: number | null;
}

export type CloudCodeSource = 'project' | 'home';

export interface CloudCodeConnection {
  settingsPath: string;
  source: CloudCodeSource;
  baseUrl: string;
  authToken: string;
  timeoutMs: string;
  env: Record<string, string>;
}

export interface CloudCodeSkill {
  id: string;
  name: string;
  description?: string;
  path: string;
  file: string;
  source: 'user' | 'plugin';
}

export type CloudCodePluginScope = 'user' | 'project' | 'local';

export interface CloudCodePlugin {
  id: string;
  name: string;
  description?: string;
  version?: string;
  author?: string;
  scope: CloudCodePluginScope;
  enabled: boolean;
  status: 'available' | 'unavailable' | 'invalid';
  installPath: string;
  manifestPath?: string;
}

export interface CloudCodeMcpServer {
  name: string;
  type: 'stdio' | 'http' | 'sse' | 'unknown';
  summary: string;
  config: Record<string, unknown>;
}

export interface CloudCodeMcpConfig {
  path: string;
  exists: boolean;
  raw: string | null;
  servers: CloudCodeMcpServer[];
  error?: string;
}

export interface CloudCodeSnapshot {
  projectPath: string;
  connection: CloudCodeConnection;
  skills: CloudCodeSkill[];
  plugins: CloudCodePlugin[];
  mcp: CloudCodeMcpConfig;
  skillsPath: string;
  pluginsPath: string;
  settingsLocalPath: string;
  settingsLocalSource: CloudCodeSource;
}

// Claude Code SDK types
export interface ClaudeCodeOptions {
  cliPath?: string;
  workingDirectory?: string;
  sessionId?: string;
  model?: string;
  maxThinkingTokens?: number;
}

export interface SDKUserMessage {
  type: 'user';
  message: {
    role: 'user';
    content: string | MessageContent[];
  };
  parent_tool_use_id: string | null;
  session_id: string;
}

export interface MessageContent {
  type: 'text' | 'image';
  text?: string;
  source?: {
    type: 'base64';
    media_type: string;
    data: string;
  };
}

// Stream event types from Claude Code
export type StreamEvent =
  | { type: 'text'; content: string }
  | { type: 'thinking'; content: string }
  | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> }
  | { type: 'tool_result'; id: string; content: string }
  | { type: 'done' }
  | { type: 'error'; content: string }
  | { type: 'session_id'; id: string };

// Permission request types
export interface PermissionRequest {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  description: string;
}

export type PermissionDecision = 'allow' | 'deny' | 'allow-always' | 'deny-always';

// IPC Channel names
export const IPC_CHANNELS = {
  // Main -> Renderer
  CLAUDE_RESPONSE: 'claude:response',
  CLAUDE_STREAM: 'claude:stream',
  CLAUDE_ERROR: 'claude:error',
  CONNECTION_STATUS: 'connection:status',
  SESSION_UPDATED: 'session:updated',
  PERMISSION_REQUEST: 'permission:request',
  SIDECAR_STATUS: 'sidecar:status',
  TEXT_SELECTION: 'text:selection',
  WINDOW_CAPTURE: 'window:capture',

  // Renderer -> Main
  SEND_MESSAGE: 'claude:send-message',
  INTERRUPT_RESPONSE: 'claude:interrupt',
  PERMISSION_RESPONSE: 'permission:response',
  CREATE_SESSION: 'session:create',
  SWITCH_SESSION: 'session:switch',
  GET_SESSIONS: 'session:get-all',
  GET_CURRENT_SESSION: 'session:get-current',
  DELETE_SESSION: 'session:delete',
  GUI_AGENT_GET_CONFIG: 'gui-agent:get-config',
  GUI_AGENT_SET_CONFIG: 'gui-agent:set-config',
  GUI_AGENT_TEST_CONNECTION: 'gui-agent:test-connection',
  SIDECAR_START: 'sidecar:start',
  SIDECAR_STOP: 'sidecar:stop',
  SIDECAR_GET_STATUS: 'sidecar:get-status',
  GET_SELECTED_TEXT: 'text:get-selected',
  INDEX_FILES: 'file:index',
  SEARCH_FILES: 'file:search',
  GET_WINDOWS: 'window:get-all',
  SEARCH_WINDOWS: 'window:search',
  CAPTURE_WINDOW: 'window:capture',
  GET_CONNECTION_STATUS: 'get-connection-status',
  CLOUD_CODE_GET_SNAPSHOT: 'cloud-code:get-snapshot',
  CLOUD_CODE_SAVE_CONNECTION: 'cloud-code:save-connection',
  CLOUD_CODE_SAVE_ENV: 'cloud-code:save-env',
  CLOUD_CODE_SET_PLUGIN_ENABLED: 'cloud-code:set-plugin-enabled',
  CLOUD_CODE_SAVE_MCP: 'cloud-code:save-mcp',
  // Window operations
  CLOSE_WINDOW: 'window:close',
  MINIMIZE_WINDOW: 'window:minimize',
  SHOW_WINDOW: 'window:show',
  HIDE_WINDOW: 'window:hide',
  TOGGLE_WINDOW: 'window:toggle',
  IS_WINDOW_OPEN: 'window:is-open',
  CREATE_DASHBOARD_WINDOW: 'window:create-dashboard',

  // File operations
  SELECT_FILE: 'file:select',
  READ_FILE: 'file:read',
} as const;

// Response handler types
export interface ResponseHandler {
  id: string;
  onChunk: (chunk: StreamEvent) => void;
  onDone: () => void;
  onError: (error: Error) => void;
}

// File reference types
export interface FileReference {
  path: string;
  content?: string;
  displayName: string;
}

export interface FileSearchResult {
  path: string;
  displayName: string;
  score: number;
}

export interface WindowInfo {
  id: number;
  title: string;
  processName: string;
  bounds: { x: number; y: number; width: number; height: number };
}

export interface WindowSearchResult {
  window: WindowInfo;
  score: number;
}

export interface SidecarStatus {
  isRunning: boolean;
  port: number | null;
  health: boolean;
}

export interface TextSelection {
  text: string;
  application: string;
  windowTitle: string;
}

// UI State types
export interface UIState {
  isChatVisible: boolean;
  isSessionListVisible: boolean;
  isThinkingExpanded: boolean;
  position: Position;
}
