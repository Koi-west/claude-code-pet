import { ipcMain, dialog, app } from 'electron';
import * as fs from 'fs';
import * as path from 'path';
import { ClaudeAgentService } from '../core/agent/ClaudeAgentService';
import { StreamController } from '../core/streams/StreamController';
import {
  IPC_CHANNELS,
  ChatMessage,
  StreamEvent,
  PermissionRequest,
  PermissionDecision,
  GuiAgentConfig,
  SidecarStatus,
} from '../types';
import { v4 as uuidv4 } from 'uuid';
import { windowManager } from './windows/WindowManager';
import { settingsStore, AppSettings } from './storage/SettingsStore';
import { shortcutManager } from './shortcuts/ShortcutManager';
import { getSidecarLauncher } from './process/sidecarLauncher';
import { getTextSelectionListener } from './listeners/textSelectionListener';
import { getFileIndexer } from './indexers/fileIndexer';
import { getWindowIndexer } from './indexers/windowIndexer';
import { getWindowCapture } from './utils/windowCapture';
import {
  loadCloudCodeSnapshot,
  saveCloudCodeConnection,
  saveCloudCodeEnv,
  setCloudCodePluginEnabled,
  saveCloudCodeMcpConfig,
} from './cloudCode';

let claudeService: ClaudeAgentService | null = null;
let streamController: StreamController | null = null;
let cloudCodeProjectPath = process.cwd();

// Permission request state
const pendingPermissions = new Map<string, {
  toolName: string;
  resolve: (value: 'allow' | 'deny' | 'allow-always' | 'deny-always') => void;
  reject: (error: Error) => void;
}>();
const permissionOverrides = new Map<string, 'allow' | 'deny'>();

const DEFAULT_GUI_AGENT_CONFIG: GuiAgentConfig = {
  sidecarUrl: 'http://127.0.0.1:8787',
  vlmProvider: 'static_openai',
  vlmBaseUrl: '',
  vlmModel: '',
  vlmApiKey: '',
  autoStartSidecar: true,
  sidecarPort: null,
};

const GUI_AGENT_CONFIG_FILE = path.join(app.getPath('userData'), 'gui-agent.json');
let guiAgentConfigCache: GuiAgentConfig = { ...DEFAULT_GUI_AGENT_CONFIG };

function loadGuiAgentConfig(): GuiAgentConfig {
  try {
    if (fs.existsSync(GUI_AGENT_CONFIG_FILE)) {
      const raw = fs.readFileSync(GUI_AGENT_CONFIG_FILE, 'utf-8');
      const parsed = JSON.parse(raw);
      return { ...DEFAULT_GUI_AGENT_CONFIG, ...parsed };
    }
  } catch (error) {
    console.warn('Failed to load GUI Agent config:', error);
  }
  return { ...DEFAULT_GUI_AGENT_CONFIG };
}

function saveGuiAgentConfig(config: GuiAgentConfig): void {
  fs.writeFileSync(GUI_AGENT_CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8');
}

function normalizeBaseUrl(rawUrl: string): string {
  const trimmed = (rawUrl || '').trim();
  if (!trimmed) {
    return '';
  }
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
}

async function fetchJson(url: string, options?: RequestInit): Promise<any> {
  const response = await fetch(url, options);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
  return text ? JSON.parse(text) : null;
}

async function testGuiAgentConnection(config: GuiAgentConfig): Promise<{ success: boolean; error?: string; health?: any }> {
  try {
    const baseUrl = normalizeBaseUrl(config.sidecarUrl);
    if (!baseUrl) {
      return { success: false, error: 'Sidecar URL is empty.' };
    }
    const health = await fetchJson(`${baseUrl}/health`);
    return { success: true, health };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

async function syncVlmConfigToSidecar(config: GuiAgentConfig): Promise<{ success: boolean; error?: string }> {
  try {
    const baseUrl = normalizeBaseUrl(config.sidecarUrl);
    if (!baseUrl) {
      return { success: false, error: 'Sidecar URL is empty.' };
    }
    if (!config.vlmBaseUrl || !config.vlmModel) {
      return { success: false, error: 'VLM base URL and model are required to sync.' };
    }

    const profileId = 'miko-vlm';
    const profileName = 'Miko VLM';

    const providerPayload: Record<string, unknown> = {
      id: profileId,
      name: profileName,
      provider: config.vlmProvider,
      model: config.vlmModel,
      apiModel: config.vlmModel,
    };

    if (config.vlmProvider === 'ollama') {
      providerPayload.ollamaBaseUrl = config.vlmBaseUrl;
      providerPayload.ollamaModel = config.vlmModel;
      providerPayload.baseUrl = config.vlmBaseUrl;
    } else {
      providerPayload.baseUrl = config.vlmBaseUrl;
      providerPayload.openaiBaseUrl = config.vlmBaseUrl;
      if (config.vlmApiKey) {
        providerPayload.apiKey = config.vlmApiKey;
      }
    }

    const profiles = await fetchJson(`${baseUrl}/settings/llm-profiles`);
    const exists = Array.isArray(profiles) && profiles.some((profile) => profile.id === profileId);

    if (exists) {
      await fetchJson(`${baseUrl}/settings/llm-profiles/${profileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(providerPayload),
      });
    } else {
      await fetchJson(`${baseUrl}/settings/llm-profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(providerPayload),
      });
    }

    await fetchJson(`${baseUrl}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vlmActiveId: profileId }),
    });

    return { success: true };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

function broadcastSettings(settings: AppSettings): void {
  windowManager.getAllWindows().forEach((win) => {
    if (!win.isDestroyed()) {
      win.webContents.send('settings:updated', settings);
    }
  });
}

function broadcastSidecarStatus(status: SidecarStatus): void {
  windowManager.getAllWindows().forEach((win) => {
    if (!win.isDestroyed()) {
      win.webContents.send(IPC_CHANNELS.SIDECAR_STATUS, status);
    }
  });
}

function shouldUpdateShortcuts(settings: Partial<AppSettings>): boolean {
  return Object.prototype.hasOwnProperty.call(settings, 'showDashboardShortcut') ||
    Object.prototype.hasOwnProperty.call(settings, 'toggleChatShortcut');
}

/**
 * Initialize the Claude service and IPC handlers
 */
export async function initializeIPC(workingDirectory?: string): Promise<void> {
  // Initialize services
  cloudCodeProjectPath = workingDirectory || process.cwd();
  claudeService = new ClaudeAgentService({
    workingDirectory: cloudCodeProjectPath,
  });

  claudeService.updateSettings(settingsStore.getSettings());
  const cloudCodeSnapshot = loadCloudCodeSnapshot(cloudCodeProjectPath);
  claudeService.setSkills(cloudCodeSnapshot.skills);

  // Load GUI Agent config
  guiAgentConfigCache = loadGuiAgentConfig();
  claudeService.setGuiAgentConfig(guiAgentConfigCache);

  streamController = new StreamController({
    typewriterSpeed: 15,
  });

  // Perform initial health check
  if (claudeService) {
    try {
      const healthStatus = await claudeService.checkConnection();
      console.log('Initial health check:', healthStatus);

  // Send status to renderer
      const petWindow = windowManager.getWindow('pet');
      if (petWindow) {
        petWindow.webContents.send(IPC_CHANNELS.CONNECTION_STATUS, healthStatus);
      }
    } catch (error) {
      console.error('Health check failed:', error);
    }
  }

  // Set up permission callback
  if (claudeService) {
    claudeService.setPermissionCallback(async (toolName, input, description) => {
      return await requestPermissionFromUser(toolName, input, description);
    });
  }

  // Set up stream controller event forwarding
  setupStreamControllerEvents();

  // Register IPC handlers
  registerHandlers();

  // Auto-start sidecar if configured
  if (guiAgentConfigCache.autoStartSidecar) {
    const sidecarLauncher = getSidecarLauncher();
    sidecarLauncher.start()
      .then(async (port) => {
        guiAgentConfigCache.sidecarPort = port;
        guiAgentConfigCache.sidecarUrl = `http://127.0.0.1:${port}`;
        claudeService?.setGuiAgentConfig(guiAgentConfigCache);
        saveGuiAgentConfig(guiAgentConfigCache);
        const status: SidecarStatus = {
          isRunning: sidecarLauncher.isSidecarRunning(),
          port: sidecarLauncher.getPort(),
          health: await sidecarLauncher.checkHealth(),
        };
        broadcastSidecarStatus(status);
      })
      .catch((error) => {
        console.warn('Failed to auto-start sidecar:', error);
      });
  }

  // Start text selection listener
  const textSelectionListener = getTextSelectionListener();
  if (process.env.MIKO_ENABLE_TEXT_SELECTION_POLLING === '1') {
    textSelectionListener.startListening();
  }

  // Background file indexing
  const fileIndexer = getFileIndexer();
  fileIndexer.indexFiles().catch((error) => {
    console.warn('Background file indexing failed:', error);
  });
}

/**
 * Set up stream controller event forwarding to renderer
 */
function setupStreamControllerEvents(): void {
  if (!streamController) return;

  streamController.on('stateChange', (state) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_STREAM, {
        type: 'stateChange',
        state,
      });
    }
  });

  streamController.on('typewriterChar', (char) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_STREAM, {
        type: 'typewriterChar',
        char,
      });
    }
  });

  streamController.on('streamEnd', (message: ChatMessage) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_RESPONSE, message);
    }
  });

  streamController.on('error', (errorMessage: string) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_ERROR, errorMessage);
    }
  });

  streamController.on('interrupted', (message: ChatMessage) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_STREAM, {
        type: 'interrupted',
        message,
      });
    }
  });

  streamController.on('toolUse', (toolCall) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_STREAM, {
        type: 'toolUse',
        toolCall,
      });
    }
  });

  streamController.on('toolResult', (result) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.CLAUDE_STREAM, {
        type: 'toolResult',
        result,
      });
    }
  });

  streamController.on('sessionId', (sessionId: string) => {
    const petWindow = windowManager.getWindow('pet');
    if (petWindow) {
      petWindow.webContents.send(IPC_CHANNELS.SESSION_UPDATED, {
        sessionId,
      });
    }
  });
}

/**
 * Request permission from user via renderer process
 */
async function requestPermissionFromUser(
  toolName: string,
  input: Record<string, unknown>,
  description: string
): Promise<'allow' | 'deny' | 'allow-always' | 'deny-always'> {
  const override = permissionOverrides.get(toolName);
  if (override) {
    return override;
  }

  const petWindow = windowManager.getWindow('pet');
  if (!petWindow) {
    throw new Error('Pet window not available');
  }

  const requestId = uuidv4();
  const request: PermissionRequest = {
    id: requestId,
    toolName,
    input,
    description,
  };

  return new Promise((resolve, reject) => {
    // Store pending request
    pendingPermissions.set(requestId, { toolName, resolve, reject });

    // Send request to renderer
    petWindow.webContents.send(IPC_CHANNELS.PERMISSION_REQUEST, request);

    // Timeout after 60 seconds
    setTimeout(() => {
      if (pendingPermissions.has(requestId)) {
        pendingPermissions.delete(requestId);
        reject(new Error('Permission request timed out'));
      }
    }, 60000);
  });
}

/**
 * Register all IPC handlers
 */
function registerHandlers(): void {
  // Sidecar management
  ipcMain.handle(IPC_CHANNELS.SIDECAR_START, async () => {
    const sidecarLauncher = getSidecarLauncher();
    try {
      const port = await sidecarLauncher.start();
      guiAgentConfigCache.sidecarPort = port;
      guiAgentConfigCache.sidecarUrl = `http://127.0.0.1:${port}`;
      claudeService?.setGuiAgentConfig(guiAgentConfigCache);
      saveGuiAgentConfig(guiAgentConfigCache);

      const status: SidecarStatus = {
        isRunning: sidecarLauncher.isSidecarRunning(),
        port: sidecarLauncher.getPort(),
        health: await sidecarLauncher.checkHealth(),
      };
      broadcastSidecarStatus(status);
      return { success: true, port, url: guiAgentConfigCache.sidecarUrl, status };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SIDECAR_STOP, async () => {
    const sidecarLauncher = getSidecarLauncher();
    sidecarLauncher.stop();
    guiAgentConfigCache.sidecarPort = null;
    guiAgentConfigCache.sidecarUrl = DEFAULT_GUI_AGENT_CONFIG.sidecarUrl;
    claudeService?.setGuiAgentConfig(guiAgentConfigCache);
    saveGuiAgentConfig(guiAgentConfigCache);

    const status: SidecarStatus = {
      isRunning: sidecarLauncher.isSidecarRunning(),
      port: sidecarLauncher.getPort(),
      health: false,
    };
    broadcastSidecarStatus(status);
    return { success: true, status };
  });

  ipcMain.handle(IPC_CHANNELS.SIDECAR_GET_STATUS, async () => {
    const sidecarLauncher = getSidecarLauncher();
    const health = await sidecarLauncher.checkHealth();
    const status: SidecarStatus = {
      isRunning: sidecarLauncher.isSidecarRunning(),
      port: sidecarLauncher.getPort(),
      health,
    };
    return { success: true, status };
  });

  // Text selection
  ipcMain.handle(IPC_CHANNELS.GET_SELECTED_TEXT, async () => {
    const textSelectionListener = getTextSelectionListener();
    const selection = textSelectionListener.getCurrentSelection();
    if (selection) {
      return { success: true, selection };
    }
    return { success: true, selection: null };
  });

  // File operations
  ipcMain.handle(IPC_CHANNELS.INDEX_FILES, async (_event, directories?: string[]) => {
    const fileIndexer = getFileIndexer();
    try {
      await fileIndexer.indexFiles(directories);
      return { success: true, fileCount: fileIndexer.getFileCount() };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SEARCH_FILES, async (_event, query: string) => {
    const fileIndexer = getFileIndexer();
    const results = fileIndexer.searchFiles(query);
    return { success: true, results };
  });

  // Window operations
  ipcMain.handle(IPC_CHANNELS.GET_WINDOWS, async () => {
    const windowIndexer = getWindowIndexer();
    await windowIndexer.updateWindows();
    return { success: true, windows: windowIndexer.getWindows() };
  });

  ipcMain.handle(IPC_CHANNELS.SEARCH_WINDOWS, async (_event, query: string) => {
    const windowIndexer = getWindowIndexer();
    const results = windowIndexer.searchWindows(query);
    return { success: true, results };
  });

  ipcMain.handle(IPC_CHANNELS.CAPTURE_WINDOW, async (_event, windowId: number) => {
    const windowCapture = getWindowCapture();
    const screenshot = await windowCapture.captureWindow(windowId);
    if (screenshot) {
      return { success: true, screenshot };
    } else {
      return { success: false, error: 'Failed to capture window' };
    }
  });

  // Message sending
  ipcMain.handle(IPC_CHANNELS.SEND_MESSAGE, async (_event, content: string) => {
    console.log('=== IPC: SEND_MESSAGE ===');
    console.log('Content:', content);

    if (!claudeService || !streamController) {
      console.error('Service not initialized');
      return { success: false, error: 'Service not initialized' };
    }

    if (!claudeService.isCliAvailable()) {
      console.error('CLI not available');
      return { success: false, error: 'Claude Code CLI not found. Please install Claude Code.' };
    }

    try {
      // Add user message
      const userMessage: ChatMessage = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: Date.now(),
      };
      claudeService.addMessage(userMessage);

      // Start streaming
      streamController.reset();
      streamController.startStream();

      console.log('=== Calling ClaudeAgentService.sendMessage ===');

      // Send message and process response
      for await (const event of claudeService.sendMessage(content)) {
        console.log('=== Stream event received ===');
        console.log('Event type:', event.type);
        if ('content' in event && event.content) {
          console.log('Event content:', event.content.substring(0, 100) + (event.content.length > 100 ? '...' : ''));
        } else if ('id' in event) {
          console.log('Event id:', event.id);
          if ('name' in event) {
            console.log('Event name:', event.name);
          }
        }
        streamController.processEvent(event);
      }

      console.log('=== Stream completed ===');

      // Add assistant message to history
      const assistantMessage = streamController.createMessage();
      claudeService.addMessage(assistantMessage);

      return { success: true, message: assistantMessage };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('=== Error during sendMessage ===');
      console.error('Error:', error);
      streamController.processEvent({ type: 'error', content: errorMessage });
      return { success: false, error: errorMessage };
    }
  });

  // Interrupt response
  ipcMain.handle(IPC_CHANNELS.INTERRUPT_RESPONSE, async () => {
    if (claudeService) {
      claudeService.interrupt();
    }
    if (streamController) {
      streamController.interrupt();
    }
    return { success: true };
  });

  // Session management
  ipcMain.handle(IPC_CHANNELS.CREATE_SESSION, async (_event, name?: string) => {
    if (!claudeService) {
      return { success: false, error: 'Service not initialized' };
    }
    claudeService.createNewSession(name);
    return { success: true, sessions: claudeService.getSessions() };
  });

  ipcMain.handle(IPC_CHANNELS.SWITCH_SESSION, async (_event, sessionId: string) => {
    if (!claudeService) {
      return { success: false, error: 'Service not initialized' };
    }
    const success = claudeService.switchSession(sessionId);
    return { success, messages: claudeService.getMessages() };
  });

  ipcMain.handle(IPC_CHANNELS.GET_SESSIONS, async () => {
    if (!claudeService) {
      return { success: false, sessions: [] };
    }
    return { success: true, sessions: claudeService.getSessions() };
  });

  ipcMain.handle(IPC_CHANNELS.GET_CURRENT_SESSION, async () => {
    if (!claudeService) {
      return { success: false, sessionId: null, messages: [] };
    }
    return {
      success: true,
      sessionId: claudeService.getSessionId(),
      messages: claudeService.getMessages(),
    };
  });

  ipcMain.handle(IPC_CHANNELS.DELETE_SESSION, async (_event, sessionId: string) => {
    if (!claudeService) {
      return { success: false, error: 'Service not initialized' };
    }
    const success = claudeService.deleteSession(sessionId);
    return { success, sessions: claudeService.getSessions() };
  });

  // Window controls
  ipcMain.on(IPC_CHANNELS.CLOSE_WINDOW, (_event, type: 'pet' | 'dashboard') => {
    windowManager.closeWindow(type);
  });

  ipcMain.on(IPC_CHANNELS.MINIMIZE_WINDOW, (_event, type: 'pet' | 'dashboard') => {
    const win = windowManager.getWindow(type);
    if (win) {
      win.minimize();
    }
  });

  ipcMain.on(IPC_CHANNELS.SHOW_WINDOW, (_event, type: 'pet' | 'dashboard') => {
    windowManager.showWindow(type);
  });

  ipcMain.on(IPC_CHANNELS.HIDE_WINDOW, (_event, type: 'pet' | 'dashboard') => {
    windowManager.hideWindow(type);
  });

  ipcMain.on(IPC_CHANNELS.TOGGLE_WINDOW, (_event, type: 'pet' | 'dashboard') => {
    windowManager.toggleWindow(type);
  });

  ipcMain.handle(IPC_CHANNELS.IS_WINDOW_OPEN, (_event, type: 'pet' | 'dashboard') => {
    return windowManager.isWindowOpen(type);
  });

  ipcMain.on(IPC_CHANNELS.CREATE_DASHBOARD_WINDOW, () => {
    windowManager.createWindow('dashboard');
  });

  // File operations
  ipcMain.handle(IPC_CHANNELS.SELECT_FILE, async () => {
    const petWindow = windowManager.getWindow('pet');
    if (!petWindow) {
      return { success: false, error: 'Window not available' };
    }

    const result = await dialog.showOpenDialog(petWindow, {
      properties: ['openFile', 'multiSelections'],
      title: 'Select file to include',
    });

    if (result.canceled || result.filePaths.length === 0) {
      return { success: false, canceled: true };
    }

    const files = result.filePaths.map((filePath) => {
      const stats = fs.statSync(filePath);
      const extension = path.extname(filePath).toLowerCase();
      return {
        path: filePath,
        displayName: path.basename(filePath),
        size: stats.size,
        type: extension,
      };
    });

    const first = files[0];
    return {
      success: true,
      files,
      path: first.path,
      displayName: first.displayName,
      size: first.size,
      type: first.type,
    };
  });

  ipcMain.handle(IPC_CHANNELS.READ_FILE, async (_event, filePath: string) => {
    try {
      const buffer = fs.readFileSync(filePath);
      const extension = path.extname(filePath).toLowerCase();
      const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'];
      const isImage = imageExtensions.includes(extension);

      if (isImage) {
        const mimeType = extension === '.jpg' ? 'image/jpeg' : `image/${extension.replace('.', '')}`;
        return {
          success: true,
          preview: {
            type: 'image',
            content: buffer.toString('base64'),
            mime: mimeType,
          },
        };
      }

      const text = buffer.toString('utf-8');
      const lines = text.split(/\r?\n/);
      const previewLines = lines.slice(0, 10).join('\n');
      return {
        success: true,
        preview: {
          type: 'text',
          content: previewLines,
          truncated: lines.length > 10,
        },
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to read file';
      return { success: false, error: errorMessage };
    }
  });

  // Connection status
  ipcMain.handle(IPC_CHANNELS.GET_CONNECTION_STATUS, async () => {
    if (!claudeService) {
      return {
        status: 'disconnected',
        cliAvailable: false,
        cliPath: null,
        sdkLoaded: false,
        error: 'Service not initialized'
      };
    }

    // Perform actual health check
    return await claudeService.checkConnection();
  });

  ipcMain.handle(IPC_CHANNELS.CLOUD_CODE_GET_SNAPSHOT, async () => {
    const snapshot = loadCloudCodeSnapshot(cloudCodeProjectPath);
    claudeService?.setSkills(snapshot.skills);
    return snapshot;
  });

  ipcMain.handle(IPC_CHANNELS.CLOUD_CODE_SAVE_CONNECTION, async (_event, updates: { baseUrl: string; authToken: string; timeoutMs: string }) => {
    return saveCloudCodeConnection(cloudCodeProjectPath, updates);
  });

  ipcMain.handle(IPC_CHANNELS.CLOUD_CODE_SAVE_ENV, async (_event, payload: { envLines: string }) => {
    return saveCloudCodeEnv(cloudCodeProjectPath, payload.envLines);
  });

  ipcMain.handle(IPC_CHANNELS.CLOUD_CODE_SET_PLUGIN_ENABLED, async (_event, payload: { pluginId: string; enabled: boolean }) => {
    return setCloudCodePluginEnabled(cloudCodeProjectPath, payload.pluginId, payload.enabled);
  });

  ipcMain.handle(IPC_CHANNELS.CLOUD_CODE_SAVE_MCP, async (_event, payload: { raw: string }) => {
    return saveCloudCodeMcpConfig(cloudCodeProjectPath, payload.raw);
  });

  ipcMain.handle(IPC_CHANNELS.GUI_AGENT_GET_CONFIG, async () => {
    return { success: true, config: guiAgentConfigCache };
  });

  ipcMain.handle(IPC_CHANNELS.GUI_AGENT_TEST_CONNECTION, async (_event, config?: GuiAgentConfig) => {
    const targetConfig = config ? { ...DEFAULT_GUI_AGENT_CONFIG, ...config } : guiAgentConfigCache;
    const result = await testGuiAgentConnection(targetConfig);
    return result;
  });

  ipcMain.handle(IPC_CHANNELS.GUI_AGENT_SET_CONFIG, async (_event, config: GuiAgentConfig, options?: { syncVlm?: boolean }) => {
    try {
      guiAgentConfigCache = { ...DEFAULT_GUI_AGENT_CONFIG, ...config };
      saveGuiAgentConfig(guiAgentConfigCache);
      claudeService?.setGuiAgentConfig(guiAgentConfigCache);

      const baseUrl = normalizeBaseUrl(guiAgentConfigCache.sidecarUrl);
      const shouldAutoStart = guiAgentConfigCache.autoStartSidecar && /localhost|127\.0\.0\.1/.test(baseUrl);
      if (shouldAutoStart && !getSidecarLauncher().isSidecarRunning()) {
        try {
          const port = await getSidecarLauncher().start();
          guiAgentConfigCache.sidecarPort = port;
          guiAgentConfigCache.sidecarUrl = `http://127.0.0.1:${port}`;
          saveGuiAgentConfig(guiAgentConfigCache);
          claudeService?.setGuiAgentConfig(guiAgentConfigCache);
        } catch (error) {
          console.warn('Failed to auto-start sidecar after config update:', error);
        }
      }

      if (options?.syncVlm) {
        const syncResult = await syncVlmConfigToSidecar(guiAgentConfigCache);
        return { success: syncResult.success, error: syncResult.error };
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Settings management
  ipcMain.handle('settings:get', async () => {
    return settingsStore.getSettings();
  });

  ipcMain.handle('settings:update', async (_event, settings: Partial<AppSettings>) => {
    const updatedSettings = settingsStore.updateSettings(settings);
    claudeService?.updateSettings(updatedSettings);
    windowManager.applySettings(updatedSettings);
    if (shouldUpdateShortcuts(settings)) {
      shortcutManager.registerShortcuts(updatedSettings);
    }
    broadcastSettings(updatedSettings);
    return updatedSettings;
  });

  ipcMain.handle('settings:set', async (_event, key: keyof AppSettings, value: any) => {
    const updatedSettings = settingsStore.set(key, value);
    claudeService?.updateSettings(updatedSettings);
    windowManager.applySettings(updatedSettings);
    if (shouldUpdateShortcuts({ [key]: value } as Partial<AppSettings>)) {
      shortcutManager.registerShortcuts(updatedSettings);
    }
    broadcastSettings(updatedSettings);
    return updatedSettings;
  });

  ipcMain.handle('settings:reset', async () => {
    const resetSettings = settingsStore.resetSettings();
    claudeService?.updateSettings(resetSettings);
    windowManager.applySettings(resetSettings);
    if (shouldUpdateShortcuts(resetSettings)) {
      shortcutManager.registerShortcuts(resetSettings);
    }
    broadcastSettings(resetSettings);
    return resetSettings;
  });

  ipcMain.handle('settings:save', async (_event, settings: AppSettings) => {
    settingsStore.saveSettings(settings);
    claudeService?.updateSettings(settings);
    windowManager.applySettings(settings);
    if (shouldUpdateShortcuts(settings)) {
      shortcutManager.registerShortcuts(settings);
    }
    broadcastSettings(settings);
    return { success: true };
  });

  // Permission response
  ipcMain.handle(IPC_CHANNELS.PERMISSION_RESPONSE, async (_event, requestId: string, decision: PermissionDecision) => {
    const pending = pendingPermissions.get(requestId);
    if (pending) {
      if (decision === 'allow-always') {
        permissionOverrides.set(pending.toolName, 'allow');
      }
      if (decision === 'deny-always') {
        permissionOverrides.set(pending.toolName, 'deny');
      }
      pending.resolve(decision);
      pendingPermissions.delete(requestId);
      return { success: true };
    }
    return { success: false, error: 'Request not found' };
  });
}

/**
 * Cleanup IPC handlers
 */
export function cleanupIPC(): void {
  if (claudeService) {
    claudeService.cleanup();
    claudeService = null;
  }

  if (streamController) {
    streamController.cleanup();
    streamController = null;
  }

  const textSelectionListener = getTextSelectionListener();
  textSelectionListener.stopListening();

  const sidecarLauncher = getSidecarLauncher();
  sidecarLauncher.stop();

  const windowCapture = getWindowCapture();
  windowCapture.cleanup();

  // Remove all handlers
  Object.values(IPC_CHANNELS).forEach((channel) => {
    ipcMain.removeHandler(channel);
    ipcMain.removeAllListeners(channel);
  });
}

/**
 * Get the Claude service instance
 */
export function getClaudeService(): ClaudeAgentService | null {
  return claudeService;
}

/**
 * Get the stream controller instance
 */
export function getStreamController(): StreamController | null {
  return streamController;
}

export default {
  initializeIPC,
  cleanupIPC,
  getClaudeService,
  getStreamController,
};
