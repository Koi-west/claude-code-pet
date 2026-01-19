import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { SessionManager } from '../session/SessionManager';
import { MessageChannel } from './MessageChannel';
import {
  StreamEvent,
  ChatMessage,
  ClaudeCodeOptions,
  SDKUserMessage,
  GuiAgentConfig,
  CloudCodeSkill
} from '../../types';
import {
  findClaudeCLIPath,
  isExistingFile,
  cliPathRequiresNode,
  getEnhancedPath,
  loadEnvironmentVariables
} from '../../utils/env';
import { z } from 'zod';

/**
 * ClaudeAgentService handles communication with Claude Code CLI.
 */
// Type definitions for SDK (imported dynamically)
type Query = any;
type SDKMessage = any;
type PermissionCallback = (toolName: string, input: Record<string, unknown>, description: string) => Promise<'allow' | 'deny' | 'allow-always' | 'deny-always'>;

export class ClaudeAgentService extends EventEmitter {
  private sessionManager: SessionManager;
  private messageChannel: MessageChannel;
  private currentQuery: Query | null = null;
  private isProcessing = false;
  private abortController: AbortController | null = null;
  private cliPath: string | null = null;
  private workingDirectory: string;
  private environmentVariables: Record<string, string>;
  private sdkModule: any = null;
  private permissionCallback: PermissionCallback | null = null;
  private guiAgentConfig: GuiAgentConfig | null = null;
  private guiAgentMcpServer: any = null;
  private model: string | null = null;
  private temperature: number | null = null;
  private maxThinkingTokens: number | null = null;
  private systemPrompt: string | null = null;
  private apiKey: string | null = null;
  private skills: CloudCodeSkill[] = [];

  constructor(options: ClaudeCodeOptions = {}) {
    super();
    this.sessionManager = new SessionManager();
    this.messageChannel = new MessageChannel();
    this.workingDirectory = options.workingDirectory || process.cwd();
    this.environmentVariables = loadEnvironmentVariables();

    if (options.cliPath) {
      this.cliPath = options.cliPath;
    } else {
      this.cliPath = findClaudeCLIPath();
    }

    if (options.sessionId) {
      this.sessionManager.setSessionId(options.sessionId);
    }

    console.log('ClaudeAgentService initialized:');
    console.log(`  CLI Path: ${this.cliPath}`);
    console.log(`  Working Directory: ${this.workingDirectory}`);
    console.log(`  Environment Variables Loaded: ${Object.keys(this.environmentVariables).length}`);
  }

  isCliAvailable(): boolean {
    return this.cliPath !== null;
  }

  getCliPath(): string | null {
    return this.cliPath;
  }

  setWorkingDirectory(dir: string): void {
    this.workingDirectory = dir;
  }

  setGuiAgentConfig(config: GuiAgentConfig | null): void {
    this.guiAgentConfig = config;
  }

  setSkills(skills: CloudCodeSkill[]): void {
    this.skills = Array.isArray(skills) ? [...skills] : [];
  }

  getSessionId(): string | null {
    return this.sessionManager.getSessionId();
  }

  getClaudeSessionId(): string | null {
    return this.sessionManager.getClaudeSessionId();
  }

  isActive(): boolean {
    return this.isProcessing;
  }

  /**
   * Check connection health by testing SDK initialization
   */
  async checkConnection(): Promise<{
    status: 'connected' | 'disconnected' | 'error';
    cliAvailable: boolean;
    cliPath: string | null;
    sdkLoaded: boolean;
    error?: string;
  }> {
    const result: {
      status: 'connected' | 'disconnected' | 'error';
      cliAvailable: boolean;
      cliPath: string | null;
      sdkLoaded: boolean;
      error?: string;
    } = {
      status: 'disconnected',
      cliAvailable: this.cliPath !== null,
      cliPath: this.cliPath,
      sdkLoaded: false,
      error: undefined,
    };

    // Check CLI path
    if (!this.cliPath) {
      result.error = 'Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code';
      return result;
    }

    // Try to load SDK module
    try {
      if (!this.sdkModule) {
        console.log('Loading SDK module for health check...');
        const dynamicImport = new Function('specifier', 'return import(specifier)');
        this.sdkModule = await dynamicImport('@anthropic-ai/claude-agent-sdk');
      }
      result.sdkLoaded = true;
      result.status = 'connected';
      return result;
    } catch (error) {
      result.error = error instanceof Error ? error.message : 'Failed to load SDK';
      result.status = 'error';
      return result;
    }
  }

  /**
   * Set permission callback for tool approval
   */
  setPermissionCallback(callback: PermissionCallback | null): void {
    this.permissionCallback = callback;
  }

  updateSettings(settings: {
    apiKey?: string;
    model?: string;
    temperature?: number;
    maxThinkingTokens?: number;
    systemPrompt?: string;
  }): void {
    if (typeof settings.apiKey === 'string') {
      this.apiKey = settings.apiKey;
    }
    if (typeof settings.model === 'string') {
      this.model = settings.model;
    }
    if (typeof settings.temperature === 'number') {
      this.temperature = settings.temperature;
    }
    if (typeof settings.maxThinkingTokens === 'number') {
      this.maxThinkingTokens = settings.maxThinkingTokens;
    }
    if (typeof settings.systemPrompt === 'string') {
      this.systemPrompt = settings.systemPrompt;
    }
  }

  async *sendMessage(content: string): AsyncGenerator<StreamEvent> {
    console.log('=== ClaudeAgentService.sendMessage (SDK) ===');

    if (!this.cliPath) {
      yield { type: 'error', content: 'Claude Code CLI not found. Please install Claude Code.' };
      return;
    }

    if (this.isProcessing) {
      console.log('=== Already processing ===');
      yield { type: 'error', content: 'Already processing a message. Please wait.' };
      return;
    }

    this.isProcessing = true;
    this.abortController = new AbortController();

    try {
      // Dynamically import SDK (ESM module)
      // Use Function constructor to avoid TypeScript converting to require()
      if (!this.sdkModule) {
        console.log('Loading SDK module...');
        const dynamicImport = new Function('specifier', 'return import(specifier)');
        this.sdkModule = await dynamicImport('@anthropic-ai/claude-agent-sdk');
        console.log('SDK module loaded');
      }

      await this.ensureGuiAgentMcpServer();

      const claudeSessionId = this.sessionManager.getClaudeSessionId();

      // Build SDK options
      const options: any = {
        cwd: this.workingDirectory,
        cliPath: this.cliPath,
        env: {
          ...process.env,
          ...this.environmentVariables,
          PATH: getEnhancedPath(undefined, this.cliPath),
        },
        abortSignal: this.abortController.signal,
      };

      if (this.apiKey) {
        options.env.ANTHROPIC_API_KEY = this.apiKey;
      }

      if (this.model) {
        options.model = this.model;
      }

      if (typeof this.temperature === 'number') {
        options.temperature = this.temperature;
      }

      if (typeof this.maxThinkingTokens === 'number') {
        options.maxThinkingTokens = this.maxThinkingTokens;
      }

      const agentModeHint = 'If the user asks to enable Agent mode or perform on-screen actions (open apps, click, type), use the gui_agent_run tool.';
      if (this.systemPrompt) {
        options.systemPrompt = `${this.systemPrompt}\n\n${agentModeHint}`;
      } else {
        options.systemPrompt = agentModeHint;
      }

      // Resume prior Claude session if available
      if (claudeSessionId) {
        options.resume = claudeSessionId;
        options.sessionId = claudeSessionId;
      }

      options.settingSources = ['user', 'project'];

      if (this.guiAgentMcpServer) {
        options.mcpServers = {
          [this.guiAgentMcpServer.name]: this.guiAgentMcpServer,
        };
      }

      // Add permission callback if set
      if (this.permissionCallback) {
        options.canUseTool = async (toolName: string, input: Record<string, unknown>) => {
          console.log('=== Permission request ===', toolName);

          if (!this.permissionCallback) {
            return { behavior: 'allow', updatedInput: input };
          }

          try {
            // Generate description for the tool
            const description = this.getToolDescription(toolName, input);

            const decision = await this.permissionCallback(toolName, input, description);

            if (decision === 'allow' || decision === 'allow-always') {
              return { behavior: 'allow', updatedInput: input };
            } else {
              return {
                behavior: 'deny',
                message: 'User denied this action.',
                interrupt: false
              };
            }
          } catch (error) {
            console.error('Permission callback error:', error);
            return {
              behavior: 'deny',
              message: 'Permission request failed.',
              interrupt: true
            };
          }
        };
      }

      console.log('Creating SDK query with options:', { cwd: options.cwd, claudeSessionId });

      // Create query using SDK
      this.currentQuery = this.sdkModule.query({
        prompt: content,
        options,
      });

      // Stream responses
      for await (const message of this.currentQuery) {
        if (this.abortController?.signal.aborted) {
          console.log('=== Stream aborted ===');
          break;
        }

        const events = this.transformSDKMessage(message);
        for (const event of events) {
          console.log('=== Yielding event ===', event.type);
          yield event;
        }
      }

      yield { type: 'done' };

    } catch (error) {
      console.error('=== Error in sendMessage ===');
      console.error(error);
      yield { type: 'error', content: error instanceof Error ? error.message : 'Unknown error' };
    } finally {
      console.log('=== FINALLY BLOCK ===');
      this.isProcessing = false;
      this.currentQuery = null;
      this.abortController = null;
    }
  }

  /**
   * Transform SDK messages to StreamEvent format
   */
  private transformSDKMessage(message: SDKMessage): StreamEvent[] {
    const events: StreamEvent[] = [];

    try {
      const msg = message as any; // Use any for now due to complex SDK types

      // Handle stream events
      if (msg.type === 'stream_event' && msg.event) {
        const event = msg.event;

        if (event.type === 'content_block_delta') {
          if (event.delta?.type === 'text_delta') {
            events.push({ type: 'text', content: event.delta.text });
          } else if (event.delta?.type === 'thinking_delta') {
            events.push({ type: 'thinking', content: event.delta.thinking });
          }
        } else if (event.type === 'content_block_start') {
          if (event.content_block?.type === 'tool_use') {
            events.push({
              type: 'tool_use',
              id: event.content_block.id,
              name: event.content_block.name,
              input: event.content_block.input || {},
            });
          }
        }
      }

      // Handle tool results
      if (msg.type === 'tool_progress' && msg.tool_use_id) {
        events.push({
          type: 'tool_result',
          id: msg.tool_use_id,
          content: msg.content || '',
        });
      }

      // Handle session initialization - save Claude SDK session ID
      if ((msg.type === 'system' || msg.type === 'result') && msg.session_id) {
        this.sessionManager.setClaudeSessionId(msg.session_id);
        this.messageChannel.setSessionId(msg.session_id);
        events.push({ type: 'session_id', id: msg.session_id });
      }

      // Handle assistant messages
      if (msg.type === 'assistant' && msg.message?.content) {
        for (const block of msg.message.content) {
          if (block.type === 'text') {
            events.push({ type: 'text', content: block.text });
          }
        }
      }

      // Handle errors in auth status
      if (msg.type === 'auth_status' && msg.error) {
        events.push({ type: 'error', content: msg.error.message || 'Authentication error' });
      }
    } catch (error) {
      console.error('Error transforming SDK message:', error);
    }

    return events;
  }

  interrupt(): void {
    console.log('=== ClaudeAgentService.interrupt ===');
    if (this.abortController) {
      this.abortController.abort();
    }

    if (this.currentQuery) {
      this.currentQuery.interrupt().catch(() => {
        // Ignore interrupt errors
      });
      this.currentQuery = null;
    }

    this.isProcessing = false;
  }

  resetSession(): void {
    this.interrupt();
    this.sessionManager.clearMessages();
    this.messageChannel.clear();
  }

  createNewSession(name?: string): void {
    this.interrupt();
    // createSession() already sets claudeSessionId to null for fresh context
    const session = this.sessionManager.createSession(name);
    this.messageChannel.setSessionId(session.id);
  }

  switchSession(sessionId: string): boolean {
    const session = this.sessionManager.getSession(sessionId);
    if (session) {
      this.interrupt();
      this.sessionManager.setSessionId(sessionId);
      this.messageChannel.setSessionId(sessionId);
      return true;
    }
    return false;
  }

  getSessions() {
    return this.sessionManager.getAllSessions();
  }

  deleteSession(sessionId: string): boolean {
    return this.sessionManager.deleteSession(sessionId);
  }

  addMessage(message: ChatMessage): void {
    this.sessionManager.addMessage(message);
  }

  getMessages(): ChatMessage[] {
    return this.sessionManager.getMessages();
  }

  cleanup(): void {
    this.interrupt();
  }

  /**
   * Generate human-readable description for tool usage
   */
  private getToolDescription(toolName: string, input: Record<string, unknown>): string {
    switch (toolName) {
      case 'Bash':
        return `Run command: ${input.command || 'unknown'}`;
      case 'Edit':
        return `Edit file: ${input.file_path || 'unknown'}`;
      case 'Write':
        return `Write to file: ${input.file_path || 'unknown'}`;
      case 'Read':
        return `Read file: ${input.file_path || 'unknown'}`;
      case 'Grep':
        return `Search for: ${input.pattern || 'unknown'}`;
      case 'Glob':
        return `Find files matching: ${input.pattern || 'unknown'}`;
      case 'gui_agent_run':
        return `Run GUI Agent task: ${input.instruction || 'unknown'}`;
      default:
        return `Use tool: ${toolName}`;
    }
  }

  private async ensureGuiAgentMcpServer(): Promise<void> {
    if (!this.sdkModule || this.guiAgentMcpServer) {
      return;
    }

    const toolDef = this.sdkModule.tool(
      'gui_agent_run',
      'Run the GUI Agent sidecar to execute on-screen tasks when the user asks to enable Agent mode or GUI Agent.',
      {
        instruction: z.string().min(1).describe('The task instruction for the GUI Agent to execute.'),
      },
      async (args: { instruction: string }) => {
        return await this.runGuiAgentTool(args.instruction);
      }
    );

    this.guiAgentMcpServer = this.sdkModule.createSdkMcpServer({
      name: 'miko-gui-agent',
      tools: [toolDef],
    });
  }

  private normalizeSidecarUrl(rawUrl: string): string {
    const trimmed = (rawUrl || '').trim();
    if (!trimmed) {
      return '';
    }
    return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
  }

  private getWebSocketConstructor(): any {
    const ctor = (global as any).WebSocket;
    if (ctor) {
      return ctor;
    }
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      return require('ws');
    } catch (error) {
      throw new Error('WebSocket is not available. Install ws or upgrade to a Node/Electron build with WebSocket support.');
    }
  }

  private async openWebSocket(url: string): Promise<any> {
    const WebSocketCtor = this.getWebSocketConstructor();
    const socket = new WebSocketCtor(url);

    await new Promise<void>((resolve, reject) => {
      socket.onopen = () => resolve();
      socket.onerror = (event: any) => reject(new Error(event?.message || 'WebSocket connection failed'));
    });

    return socket;
  }

  private async runGuiAgentTool(instruction: string): Promise<any> {
    const config = this.guiAgentConfig;
    if (!config) {
      return {
        isError: true,
        content: [{ type: 'text', text: 'GUI Agent is not configured. Open settings and set the sidecar URL and VLM details first.' }],
      };
    }

    const baseUrl = this.normalizeSidecarUrl(config.sidecarUrl);
    if (!baseUrl) {
      return {
        isError: true,
        content: [{ type: 'text', text: 'GUI Agent sidecar URL is missing. Open settings and set it before running.' }],
      };
    }

    const sessionId = uuidv4();
    let chatSocket: any = null;
    try {
      chatSocket = await this.openWebSocket(`${baseUrl}/chat?session_id=${sessionId}`);
    } catch (error) {
      return {
        isError: true,
        content: [{ type: 'text', text: `Failed to open GUI Agent chat session: ${error instanceof Error ? error.message : 'Unknown error'}` }],
      };
    }

    try {
      const runResponse = await fetch(`${baseUrl}/gui-agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          instruction,
        }),
      });

      if (!runResponse.ok) {
        const errorText = await runResponse.text();
        return {
          isError: true,
          content: [{ type: 'text', text: `GUI Agent run failed (${runResponse.status}): ${errorText}` }],
        };
      }

      const runData = await runResponse.json();
      const runId = runData.run_id;
      if (!runId) {
        return {
          isError: true,
          content: [{ type: 'text', text: 'GUI Agent run response missing run_id.' }],
        };
      }

      const summary = await this.collectGuiAgentEvents(baseUrl, runId, sessionId);
      return {
        content: [{ type: 'text', text: summary }],
      };
    } catch (error) {
      return {
        isError: true,
        content: [{ type: 'text', text: `GUI Agent error: ${error instanceof Error ? error.message : 'Unknown error'}` }],
      };
    } finally {
      if (chatSocket) {
        chatSocket.close();
      }
    }
  }

  private async collectGuiAgentEvents(baseUrl: string, runId: string, sessionId: string): Promise<string> {
    const WebSocketCtor = this.getWebSocketConstructor();
    const wsUrl = `${baseUrl}/gui-agent/stream?run_id=${encodeURIComponent(runId)}&session_id=${encodeURIComponent(sessionId)}`;
    const socket = new WebSocketCtor(wsUrl);
    const lines: string[] = [];
    const maxLines = 80;
    let finalStatus = 'completed';

    const pushLine = (line: string) => {
      if (lines.length < maxLines) {
        lines.push(line);
      }
    };

    const donePromise = new Promise<string>((resolve, reject) => {
      socket.onopen = () => {
        pushLine('GUI Agent stream connected.');
      };
      socket.onmessage = (event: any) => {
        try {
          const data = JSON.parse(event.data);
          const payload = data?.payload || data;
          const type = payload?.type;
          const message = payload?.message;
          if (type === 'error') {
            finalStatus = 'error';
          }
          if (type && message) {
            pushLine(`[${type}] ${message}`);
          } else if (payload) {
            pushLine(JSON.stringify(payload));
          }
        } catch (error) {
          pushLine(`(unparsed) ${event.data}`);
        }
      };
      socket.onerror = (event: any) => {
        reject(new Error(event?.message || 'GUI Agent stream error'));
      };
      socket.onclose = () => {
        resolve(finalStatus);
      };
    });

    const timeoutMs = 5 * 60 * 1000;
    const timeoutPromise = new Promise<string>((_resolve, reject) => {
      setTimeout(() => reject(new Error('GUI Agent stream timed out.')), timeoutMs);
    });

    try {
      await Promise.race([donePromise, timeoutPromise]);
    } catch (error) {
      finalStatus = 'error';
      pushLine(`Stream error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      socket.close();
    }

    if (lines.length === 0) {
      return `GUI Agent finished (${finalStatus}). No events received.`;
    }
    return `GUI Agent finished (${finalStatus}).\n\n${lines.join('\n')}`;
  }
}

export default ClaudeAgentService;
