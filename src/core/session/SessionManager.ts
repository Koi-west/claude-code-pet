import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { v4 as uuidv4 } from 'uuid';
import { Session, SessionInfo, ChatMessage } from '../../types';

/**
 * SessionManager handles conversation session lifecycle and persistence.
 * Sessions are stored as JSONL files in the user's home directory.
 */
export class SessionManager {
  private sessions: Map<string, Session> = new Map();
  private currentSessionId: string | null = null;
  private claudeSessionId: string | null = null; // Claude Code SDK session ID
  private storageDir: string;

  constructor() {
    // Store sessions in ~/.miko-pet/sessions/
    this.storageDir = path.join(os.homedir(), '.miko-pet', 'sessions');
    this.ensureStorageDir();
    this.loadSessions();
  }

  private ensureStorageDir(): void {
    if (!fs.existsSync(this.storageDir)) {
      fs.mkdirSync(this.storageDir, { recursive: true });
    }
  }

  private loadSessions(): void {
    try {
      const files = fs.readdirSync(this.storageDir);
      for (const file of files) {
        if (file.endsWith('.json')) {
          const filePath = path.join(this.storageDir, file);
          const content = fs.readFileSync(filePath, 'utf-8');
          const session = JSON.parse(content) as Session;
          this.sessions.set(session.id, session);
        }
      }
    } catch (error) {
      console.warn('[SessionManager] Failed to load sessions:', error);
    }
  }

  private saveSession(session: Session): void {
    try {
      const filePath = path.join(this.storageDir, `${session.id}.json`);
      fs.writeFileSync(filePath, JSON.stringify(session, null, 2), 'utf-8');
    } catch (error) {
      console.error('[SessionManager] Failed to save session:', error);
    }
  }

  /**
   * Create a new session
   */
  createSession(name?: string): Session {
    const id = uuidv4();
    const now = Date.now();
    const session: Session = {
      id,
      name: name || `Session ${this.sessions.size + 1}`,
      createdAt: now,
      lastAccessedAt: now,
      messages: [],
      claudeSessionId: null, // Start with null to create fresh Claude context
    };

    this.sessions.set(id, session);
    this.currentSessionId = id;
    this.claudeSessionId = null; // Reset Claude session ID for fresh context
    this.saveSession(session);

    return session;
  }

  /**
   * Get the current session, creating one if none exists
   */
  getCurrentSession(): Session {
    if (this.currentSessionId && this.sessions.has(this.currentSessionId)) {
      const session = this.sessions.get(this.currentSessionId)!;

      // Ensure claudeSessionId is in sync with session data
      if (this.claudeSessionId !== session.claudeSessionId) {
        this.claudeSessionId = session.claudeSessionId || null;
      }

      return session;
    }

    // Create a default session if none exists
    return this.createSession('Default');
  }

  /**
   * Get the current session ID
   */
  getSessionId(): string | null {
    return this.currentSessionId;
  }

  /**
   * Set the current session ID
   */
  setSessionId(id: string): void {
    if (this.sessions.has(id)) {
      this.currentSessionId = id;
      const session = this.sessions.get(id)!;
      session.lastAccessedAt = Date.now();

      // Restore claudeSessionId from session
      this.claudeSessionId = session.claudeSessionId || null;

      this.saveSession(session);
    }
  }

  /**
   * Get the Claude Code SDK session ID
   */
  getClaudeSessionId(): string | null {
    return this.claudeSessionId;
  }

  /**
   * Set the Claude Code SDK session ID and save it
   */
  setClaudeSessionId(id: string | null): void {
    this.claudeSessionId = id;

    // Save to current session
    const session = this.getCurrentSession();
    session.claudeSessionId = id;
    this.saveSession(session);
  }

  /**
   * Get a session by ID
   */
  getSession(id: string): Session | undefined {
    return this.sessions.get(id);
  }

  /**
   * Get all sessions as info objects
   */
  getAllSessions(): SessionInfo[] {
    return Array.from(this.sessions.values())
      .map((session) => ({
        id: session.id,
        name: session.name,
        createdAt: session.createdAt,
        lastAccessedAt: session.lastAccessedAt,
        messageCount: session.messages.length,
      }))
      .sort((a, b) => b.lastAccessedAt - a.lastAccessedAt);
  }

  /**
   * Delete a session
   */
  deleteSession(id: string): boolean {
    if (!this.sessions.has(id)) {
      return false;
    }

    this.sessions.delete(id);

    // Remove the session file
    const filePath = path.join(this.storageDir, `${id}.json`);
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch (error) {
      console.warn('[SessionManager] Failed to delete session file:', error);
    }

    // If this was the current session, switch to another or create new
    if (this.currentSessionId === id) {
      const remaining = Array.from(this.sessions.values());
      if (remaining.length > 0) {
        this.currentSessionId = remaining[0].id;
      } else {
        this.currentSessionId = null;
      }
    }

    return true;
  }

  /**
   * Add a message to the current session
   */
  addMessage(message: ChatMessage): void {
    const session = this.getCurrentSession();
    session.messages.push(message);
    session.lastAccessedAt = Date.now();
    this.saveSession(session);
  }

  /**
   * Update the last message in the current session
   */
  updateLastMessage(content: string, isStreaming: boolean = false): void {
    const session = this.getCurrentSession();
    if (session.messages.length > 0) {
      const lastMessage = session.messages[session.messages.length - 1];
      lastMessage.content = content;
      lastMessage.isStreaming = isStreaming;
      this.saveSession(session);
    }
  }

  /**
   * Get messages from the current session
   */
  getMessages(): ChatMessage[] {
    const session = this.getCurrentSession();
    return session.messages;
  }

  /**
   * Clear messages from the current session
   */
  clearMessages(): void {
    const session = this.getCurrentSession();
    session.messages = [];
    session.lastAccessedAt = Date.now();
    this.saveSession(session);
  }

  /**
   * Rename a session
   */
  renameSession(id: string, newName: string): boolean {
    const session = this.sessions.get(id);
    if (!session) {
      return false;
    }

    session.name = newName;
    session.lastAccessedAt = Date.now();
    this.saveSession(session);
    return true;
  }
}

export default SessionManager;
